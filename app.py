import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# Dashboard Configuration
st.set_page_config(page_title="OATY 3.0 Operations Analytics", layout="wide")

# Custom Styling for Premium Look
st.markdown("""
    <style>
    .main { background-color: #f8faff; }
    [data-testid="stMetricValue"] { font-size: 1.8rem; color: #1e3a8a; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.05); border: 1px solid #e5e7eb; }
    h1, h2, h3 { color: #1e3a8a; font-family: 'Inter', sans-serif; font-weight: 700; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA LOADING (READING DIRECTLY FROM EXCEL)
# ---------------------------------------------------------
@st.cache_data
def load_data(file_path):
    try:
        # Load primary volume planning (Appendix 1.5)
        df_vol = pd.read_excel(file_path, sheet_name='Appendix 1.5', skiprows=3)
        df_vol.columns = [c.strip() for c in df_vol.columns]
        
        # Load segment data (Appendix 1.3)
        df_seg = pd.read_excel(file_path, sheet_name='Appendix 1.3', skiprows=2)
        df_seg.columns = [c.strip() for c in df_seg.columns]
        
        # Load core assumptions
        df_inputs = pd.read_excel(file_path, sheet_name='Inputs and Assumptions')
        
        return df_vol, df_seg, df_inputs
    except Exception as e:
        st.error(f"Error loading Excel file: {e}. Ensure the file is named 'OATY_Aadit.xlsx' and contains the correct sheets.")
        return None, None, None

# Main Data Load
FILE_NAME = 'OATY_Aadit.xlsx'
df_vol, df_seg, df_inputs = load_data(FILE_NAME)

if df_vol is not None:
    # ---------------------------------------------------------
    # SIDEBAR CONTROLS
    # ---------------------------------------------------------
    st.sidebar.title("Operations Control")
    st.sidebar.markdown("---")

    scenario_name = st.sidebar.selectbox("Demand Scenario", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
    multiplier = 1.15 if "Peak" in scenario_name else (0.85 if "Slow" in scenario_name else 1.0)

    strategy = st.sidebar.selectbox("Fulfillment Strategy", 
                                   ["Chase (Overtime Priority)", "Level Production", "Subcontract Heavy", "Hybrid"])

    st.sidebar.markdown("### Cost Parameters")
    # Pulling default 0.2, 1.5, 1.25 from the Excel logic
    h_cost_pct = st.sidebar.slider("Annual Holding Cost (%)", 0, 50, 20) / 100
    ot_mult = st.sidebar.slider("Overtime Rate (Multiplier)", 1.0, 2.5, 1.5)
    sub_mult = st.sidebar.slider("Subcontract Rate (Multiplier)", 1.0, 2.0, 1.25)
    inc_sunday = st.sidebar.toggle("Enable Sunday OT (2.0x)", value=False)

    # ---------------------------------------------------------
    # ANALYTICS ENGINE
    # ---------------------------------------------------------
    def run_simulation(demand_mult, strat, hc, ot_m, sub_m, sunday):
        BASE_WEEKLY_CAP = 16500
        # OT Limit: 10 hrs weekday + 8 hrs Sat = 18 hrs (Approx 45% of 40hr base)
        OT_LIMIT_WEEKLY = 7425 
        if sunday: OT_LIMIT_WEEKLY += 3300 
        
        df = df_vol.copy().head(12) # Ensure only 12 months
        df['Demand'] = df['Total months\' demand'] * demand_mult
        df['Base_Cap'] = df['Production weeks'] * BASE_WEEKLY_CAP
        df['Max_OT_Cap'] = df['Production weeks'] * OT_LIMIT_WEEKLY
        
        prod, ot, sub, inv = [], [], [], [0]
        total_ann_demand = df['Demand'].sum()
        total_weeks = df['Production weeks'].sum()
        level_weekly_target = total_ann_demand / total_weeks
        
        curr_inv = 0
        for i, row in df.iterrows():
            d, bc, mot = row['Demand'], row['Base_Cap'], row['Max_OT_Cap']
            p_val, o_val, s_val = 0, 0, 0
            
            if strat == "Chase (Overtime Priority)":
                p_val = bc
                net = d - bc - curr_inv
                if net > 0:
                    o_val = min(net, mot)
                    s_val = max(0, net - o_val)
                    curr_inv = 0
                else:
                    curr_inv = -net
            elif strat == "Level Production":
                target = level_weekly_target * row['Production weeks']
                p_val = min(target, bc)
                o_val = min(max(0, target - bc), mot)
                s_val = max(0, target - bc - o_val)
                curr_inv += (p_val + o_val + s_val) - d
                if curr_inv < 0:
                    s_val += abs(curr_inv); curr_inv = 0
            elif strat == "Subcontract Heavy":
                p_val = bc
                net = d - bc - curr_inv
                if net > 0:
                    s_val = net; curr_inv = 0
                else:
                    curr_inv = -net
            else: # Hybrid
                p_val = bc
                net = d - bc - curr_inv
                if net > 0:
                    o_val = min(net, mot * 0.5)
                    s_val = max(0, net - o_val); curr_inv = 0
                else:
                    curr_inv = -net
            
            prod.append(p_val); ot.append(o_val); sub.append(s_val); inv.append(curr_inv)
            
        df['Standard_Prod'], df['OT_Units'], df['Sub_Units'], df['Ending_Inv'] = prod, ot, sub, inv[1:]
        df['Total_Cost'] = (df['Standard_Prod'] * 1.0) + (df['OT_Units'] * ot_m) + \
                           (df['Sub_Units'] * sub_m) + (df['Ending_Inv'] * (hc/12))
        return df

    results = run_simulation(multiplier, strategy, h_cost_pct, ot_mult, sub_mult, inc_sunday)

    # ---------------------------------------------------------
    # DASHBOARD UI
    # ---------------------------------------------------------
    st.title("🏙 OATY 3.0 Operational Planning Dashboard")
    
    # KPI Row
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Annual Demand", f"{results['Demand'].sum():,.0f}")
    util = (results['Standard_Prod'] + results['OT_Units']).sum() / (results['Base_Cap'].sum() + results['Max_OT_Cap'].sum())
    k2.metric("Avg Utilization", f"{util:.1%}")
    k3.metric("Max Inventory", f"{results['Ending_Inv'].max():,.0f}")
    k4.metric("Total Est. Cost", f"${results['Total_Cost'].sum():,.0f}")

    # Visualizations
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Monthly Demand vs. Base Capacity")
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=results['Month'], y=results['Demand'], name="Demand", line=dict(color='#1e3a8a', width=3)))
        fig.add_trace(go.Bar(x=results['Month'], y=results['Base_Cap'], name="Base Cap", marker_color='#bfdbfe'))
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Fulfillment Strategy Breakdown")
        fig = px.bar(results, x='Month', y=['Standard_Prod', 'OT_Units', 'Sub_Units'], 
                     color_discrete_map={'Standard_Prod':'#1e3a8a', 'OT_Units':'#3b82f6', 'Sub_Units':'#93c5fd'})
        st.plotly_chart(fig, use_container_width=True)

    # Strategy Comparison Table
    st.markdown("---")
    st.subheader("Strategy Financial Benchmarking")
    comparison = []
    for s in ["Chase (Overtime Priority)", "Level Production", "Subcontract Heavy", "Hybrid"]:
        res_s = run_simulation(multiplier, s, h_cost_pct, ot_mult, sub_mult, inc_sunday)
        comparison.append({"Strategy": s, "Total Cost": res_s['Total_Cost'].sum(), "Max Inv": res_s['Ending_Inv'].max()})
    
    comp_df = pd.DataFrame(comparison)
    st.table(comp_df.style.format({"Total Cost": "${:,.0f}", "Max Inv": "{:,.0f}"}))

    # Insights
    st.info(f"💡 **Recommendation:** The **{comp_df.loc[comp_df['Total Cost'].idxmin(), 'Strategy']}** strategy is the most cost-effective for the {scenario_name} scenario.")

else:
    st.warning("Please ensure 'OATY_Aadit.xlsx' is in the same directory as this script.")
