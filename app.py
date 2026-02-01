import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Dashboard Configuration
st.set_page_config(page_title="OATY 3.0 Operations Analytics", layout="wide")

# Premium Blue Theme CSS
st.markdown("""
    <style>
    .main { background-color: #f8faff; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1e3a8a; font-weight: bold; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 15px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border-left: 5px solid #1e3a8a; }
    h1, h2, h3 { color: #1e3a8a; font-family: 'Segoe UI', sans-serif; }
    .stButton>button { background-color: #1e3a8a; color: white; border-radius: 8px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA ENGINE: LOADING & PREPROCESSING
# ---------------------------------------------------------
@st.cache_data
def load_and_clean_data(file_path):
    try:
        # Load Volume Planning (Appendix 1.5)
        df_vol = pd.read_excel(file_path, sheet_name='Appendix 1.5', skiprows=3)
        df_vol.columns = [c.strip() for c in df_vol.columns]
        df_vol = df_vol.dropna(subset=['Month']).head(12)

        # Load Segment Mix (Appendix 1.3)
        df_seg = pd.read_excel(file_path, sheet_name='Appendix 1.3', skiprows=2)
        df_seg.columns = [c.strip() for c in df_seg.columns]
        df_seg = df_seg.dropna(subset=['Month']).head(12)

        return df_vol, df_seg
    except Exception as e:
        st.error(f"Data Load Error: Ensure {file_path} exists with sheets 'Appendix 1.5' and 'Appendix 1.3'.")
        return None, None

df_vol, df_seg = load_and_clean_data('OATY_Aadit.xlsx')

if df_vol is not None:
    # ---------------------------------------------------------
    # SIDEBAR CONTROLS
    # ---------------------------------------------------------
    st.sidebar.header("🛠 Strategy Control Panel")
    
    scenario_choice = st.sidebar.selectbox("Demand Scenario", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
    multiplier = 1.15 if scenario_choice == "Peak (+15%)" else (0.85 if scenario_choice == "Slow (-15%)" else 1.0)
    
    strategy = st.sidebar.selectbox("Operational Strategy", 
                                   ["Chase (OT Priority)", "Level Production", "Subcontract Heavy", "Hybrid"])

    st.sidebar.markdown("---")
    st.sidebar.subheader("Cost Adjustments")
    h_rate = st.sidebar.slider("Annual Holding Cost %", 0, 50, 20) / 100
    ot_m = st.sidebar.slider("Overtime Cost Multiplier", 1.0, 2.5, 1.5)
    sub_m = st.sidebar.slider("Subcontract Multiplier", 1.0, 2.0, 1.25)
    sun_ot = st.sidebar.toggle("Include Sunday OT", value=False)

    # ---------------------------------------------------------
    # ANALYTICS LOGIC (STEP 1 - 4)
    # ---------------------------------------------------------
    def run_analytics(d_mult, strat, hc, ot_mult, sub_mult, sunday):
        BASE_CAP_WEEKLY = 16500
        # OT Limit: 10 hrs weekday + 8 hrs Sat = 18 hrs total (45% of 40hr base)
        OT_CAP_WEEKLY = 7425 
        if sunday: OT_CAP_WEEKLY += 3300 # Add Sunday 8 hrs
        
        results = df_vol.copy()
        results['Forecasted_Demand'] = results['Total months\' demand'] * d_mult
        results['Regular_Capacity'] = results['Production weeks'] * BASE_CAP_WEEKLY
        results['Max_OT_Capacity'] = results['Production weeks'] * OT_CAP_WEEKLY
        
        # Strategy Execution
        prod, ot, sub, inv = [], [], [], [0]
        level_target = results['Forecasted_Demand'].sum() / results['Production weeks'].sum()
        
        curr_inv = 0
        for i, row in results.iterrows():
            demand = row['Forecasted_Demand']
            reg_cap = row['Regular_Capacity']
            ot_cap = row['Max_OT_Capacity']
            
            p_val, o_val, s_val = 0, 0, 0
            
            if strat == "Chase (OT Priority)":
                p_val = reg_cap
                gap = demand - p_val - curr_inv
                if gap > 0:
                    o_val = min(gap, ot_cap)
                    s_val = max(0, gap - o_val)
                    curr_inv = 0
                else:
                    curr_inv = abs(gap)
            
            elif strat == "Level Production":
                target_output = level_target * row['Production weeks']
                p_val = min(target_output, reg_cap)
                o_val = min(max(0, target_output - reg_cap), ot_cap)
                s_val = max(0, target_output - reg_cap - o_val)
                curr_inv += (p_val + o_val + s_val) - demand
                if curr_inv < 0:
                    s_val += abs(curr_inv); curr_inv = 0
            
            elif strat == "Subcontract Heavy":
                p_val = reg_cap
                gap = demand - p_val - curr_inv
                if gap > 0:
                    s_val = gap
                    curr_inv = 0
                else:
                    curr_inv = abs(gap)
            
            else: # Hybrid: 50% OT then Subcontract
                p_val = reg_cap
                gap = demand - p_val - curr_inv
                if gap > 0:
                    o_val = min(gap, ot_cap * 0.5)
                    s_val = max(0, gap - o_val)
                    curr_inv = 0
                else:
                    curr_inv = abs(gap)
            
            prod.append(p_val); ot.append(o_val); sub.append(s_val); inv.append(curr_inv)

        results['Standard_Units'] = prod
        results['OT_Units'] = ot
        results['Sub_Units'] = sub
        results['Ending_Inventory'] = inv[1:]
        
        # Financial Computation
        results['Base_Cost'] = results['Standard_Units'] * 1.0
        results['OT_Cost'] = results['OT_Units'] * ot_mult
        results['Sub_Cost'] = results['Sub_Units'] * sub_mult
        results['Hold_Cost'] = results['Ending_Inventory'] * (hc / 12)
        results['Total_Monthly_Cost'] = results['Base_Cost'] + results['OT_Cost'] + results['Sub_Cost'] + results['Hold_Cost']
        
        return results

    main_res = run_analytics(multiplier, strategy, h_rate, ot_m, sub_m, sun_ot)

    # ---------------------------------------------------------
    # SECTION 1: KPI CARDS
    # ---------------------------------------------------------
    st.title("🏙 OATY 3.0 Operational Planning Engine")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total Demand", f"{main_res['Forecasted_Demand'].sum():,.0f}")
    k2.metric("Avg Capacity Util", f"{(main_res['Standard_Units'].sum()+main_res['OT_Units'].sum())/ (main_res['Regular_Capacity'].sum()+main_res['Max_OT_Capacity'].sum()):.1%}")
    k3.metric("Max Inventory", f"{main_res['Ending_Inventory'].max():,.0f}")
    k4.metric("Estimated Total Cost", f"${main_res['Total_Monthly_Cost'].sum():,.0f}")

    # ---------------------------------------------------------
    # SECTION 2: GRAPHS
    # ---------------------------------------------------------
    st.markdown("---")
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("Monthly Demand vs. Base Capacity")
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(x=main_res['Month'], y=main_res['Regular_Capacity'], name="Standard Capacity", marker_color='#bfdbfe'))
        fig1.add_trace(go.Scatter(x=main_res['Month'], y=main_res['Forecasted_Demand'], name="Demand", line=dict(color='#1e3a8a', width=4)))
        fig1.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig1, use_container_width=True)

    with g2:
        st.subheader("Inventory Levels & Storage Ceiling")
        fig2 = px.area(main_res, x='Month', y='Ending_Inventory', color_discrete_sequence=['#3b82f6'])
        fig2.add_hline(y=20000, line_dash="dash", line_color="red", annotation_text="Whse Limit (20k)")
        fig2.update_layout(template="plotly_white")
        st.plotly_chart(fig2, use_container_width=True)

    

    g3, g4 = st.columns(2)
    with g3:
        st.subheader("Fulfillment Mix (OT vs Subcontract)")
        fig3 = px.bar(main_res, x='Month', y=['OT_Units', 'Sub_Units'], barmode='stack',
                      color_discrete_map={'OT_Units':'#1e40af', 'Sub_Units':'#60a5fa'})
        fig3.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig3, use_container_width=True)
    
    with g4:
        st.subheader("Product Segment Mix")
        fig4 = px.line(df_seg, x='Month', y=['Consumer', 'PC', 'Professional'], markers=True,
                       color_discrete_sequence=['#1e3a8a', '#3b82f6', '#93c5fd'])
        fig4.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.1))
        st.plotly_chart(fig4, use_container_width=True)

    # ---------------------------------------------------------
    # SECTION 3 & 4: STRATEGY COMPARISON & INSIGHTS
    # ---------------------------------------------------------
    st.markdown("---")
    st.subheader("Strategic Benchmarking")
    
    strats = ["Chase (OT Priority)", "Level Production", "Subcontract Heavy", "Hybrid"]
    comparison = []
    for s in strats:
        res_s = run_analytics(multiplier, s, h_rate, ot_m, sub_m, sun_ot)
        comparison.append({
            "Strategy": s,
            "Annual Cost": res_s['Total_Monthly_Cost'].sum(),
            "Total Subcontracted": res_s['Sub_Units'].sum(),
            "Max Inventory": res_s['Ending_Inventory'].max()
        })
    
    comp_df = pd.DataFrame(comparison)
    st.table(comp_df.style.highlight_min(subset=['Annual Cost'], color='#dcfce7').format({"Annual Cost": "${:,.0f}", "Max Inventory": "{:,.0f}"}))

    # Automated Insights
    best_s = comp_df.loc[comp_df['Annual Cost'].idxmin(), 'Strategy']
    bottlenecks = main_res[main_res['Sub_Units'] > 0]['Month'].tolist()
    
    st.markdown("### 🔍 Engineering Insights")
    c_in1, c_in2 = st.columns(2)
    with c_in1:
        st.info(f"**Bottleneck Identification:** Months requiring external subcontracting: {', '.join(bottlenecks) if bottlenecks else 'None'}.")
    with c_in2:
        st.success(f"**Optimization Result:** The **{best_s}** strategy is the most cost-efficient path for the {scenario_choice} scenario.")

else:
    st.error("FileNotFound: Please ensure OATY_Aadit.xlsx is in the same folder as this script.")
