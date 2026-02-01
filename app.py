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
    .sidebar .sidebar-content { background-image: linear-gradient(#1e3a8a, #1e40af); color: white; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA LOADING (FROM EXCEL EXHIBITS)
# ---------------------------------------------------------
@st.cache_data
def load_data():
    # Load primary volume planning (Appendix 1.5)
    df_vol = pd.read_csv('OATY_Aadit.xlsx - Appendix 1.5.csv', skiprows=3)
    df_vol.columns = [c.strip() for c in df_vol.columns]
    
    # Load segment data (Appendix 1.3)
    df_seg = pd.read_csv('OATY_Aadit.xlsx - Appendix 1.3.csv', skiprows=2)
    df_seg.columns = [c.strip() for c in df_seg.columns]
    
    return df_vol, df_seg

df_vol, df_seg = load_data()

# ---------------------------------------------------------
# SIDEBAR CONTROLS
# ---------------------------------------------------------
st.sidebar.image("https://img.icons8.com/fluency/96/factory.png", width=80)
st.sidebar.title("Operations Control")
st.sidebar.markdown("---")

# Scenarios
scenario_name = st.sidebar.selectbox("Demand Scenario", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
multiplier = 1.0
if scenario_name == "Peak (+15%)": multiplier = 1.15
elif scenario_name == "Slow (-15%)": multiplier = 0.85

# Strategy
strategy = st.sidebar.selectbox("Fulfillment Strategy", ["Chase (Overtime Priority)", "Level Production", "Subcontract Heavy", "Hybrid"])

st.sidebar.markdown("### Cost Parameters")
h_cost_pct = st.sidebar.slider("Annual Holding Cost (%)", 0, 50, 20) / 100
ot_mult = st.sidebar.slider("Overtime Rate (Multiplier)", 1.0, 2.5, 1.5)
sub_mult = st.sidebar.slider("Subcontract Rate (Multiplier)", 1.0, 2.0, 1.25)

st.sidebar.markdown("### Capacity Settings")
inc_sunday = st.sidebar.toggle("Enable Sunday OT (2.0x)", value=False)

# ---------------------------------------------------------
# ANALYTICS ENGINE
# ---------------------------------------------------------
def run_simulation(demand_mult, strat, hc, ot_m, sub_m, sunday):
    BASE_WEEKLY_CAP = 16500
    # Overtime units: 10 hrs weekday + 8 hrs Sat = 18 hrs (45% of 40hr base)
    OT_LIMIT_WEEKLY = 7425 
    if sunday: OT_LIMIT_WEEKLY += 3300 # Add 8 hrs Sunday
    
    df = df_vol.copy()
    df['Demand'] = df['Total months\' demand'] * demand_mult
    df['Base_Cap'] = df['Production weeks'] * BASE_WEEKLY_CAP
    df['Max_OT_Cap'] = df['Production weeks'] * OT_LIMIT_WEEKLY
    
    # Strategy Logic
    prod, ot, sub, inv = [], [], [], [0]
    total_ann_demand = df['Demand'].sum()
    total_weeks = df['Production weeks'].sum()
    level_weekly_target = total_ann_demand / total_weeks
    
    curr_inv = 0
    for i, row in df.iterrows():
        d = row['Demand']
        bc = row['Base_Cap']
        mot = row['Max_OT_Cap']
        
        p_val, o_val, s_val = 0, 0, 0
        
        if strat == "Chase (Overtime Priority)":
            net = d - bc - curr_inv
            p_val = bc
            if net > 0:
                o_val = min(net, mot)
                s_val = max(0, net - o_val)
                curr_inv = 0
            else:
                curr_inv = -net
                
        elif strat == "Level Production":
            p_val = level_weekly_target * row['Production weeks']
            # Regular production over base_cap is treated as OT
            if p_val > bc:
                o_val = min(p_val - bc, mot)
                s_val = max(0, (p_val - bc) - o_val)
                p_val = bc
            
            curr_inv += (p_val + o_val + s_val) - d
            if curr_inv < 0: # If even level production fails, subcontract the gap
                s_val += abs(curr_inv)
                curr_inv = 0
                
        elif strat == "Subcontract Heavy":
            p_val = bc
            net = d - bc - curr_inv
            if net > 0:
                s_val = net
                curr_inv = 0
            else:
                curr_inv = -net
        
        else: # Hybrid: 50% OT then Subcontract
            p_val = bc
            net = d - bc - curr_inv
            if net > 0:
                o_val = min(net, mot * 0.5)
                s_val = max(0, net - o_val)
                curr_inv = 0
            else:
                curr_inv = -net
        
        prod.append(p_val); ot.append(o_val); sub.append(s_val); inv.append(curr_inv)
        
    df['Standard_Prod'] = prod
    df['OT_Units'] = ot
    df['Sub_Units'] = sub
    df['Ending_Inv'] = inv[1:]
    
    # Financials (Base unit cost = 1)
    df['Cost_Base'] = df['Standard_Prod'] * 1.0
    df['Cost_OT'] = df['OT_Units'] * ot_m
    df['Cost_Sub'] = df['Sub_Units'] * sub_m
    df['Cost_Hold'] = df['Ending_Inv'] * (hc / 12)
    df['Total_Cost'] = df['Cost_Base'] + df['Cost_OT'] + df['Cost_Sub'] + df['Cost_Hold']
    
    return df

results = run_simulation(multiplier, strategy, h_cost_pct, ot_mult, sub_mult, inc_sunday)

# ---------------------------------------------------------
# DASHBOARD UI
# ---------------------------------------------------------
st.title("🏙 OATY 3.0 Operational Planning Dashboard")
st.markdown(f"**Current View:** {scenario_name} | **Strategy:** {strategy}")

# KPI Row
k1, k2, k3, k4 = st.columns(4)
k1.metric("Annual Demand", f"{results['Demand'].sum():,.0f}")
util = (results['Standard_Prod'] + results['OT_Units']).sum() / (results['Base_Cap'] + results['Max_OT_Cap']).sum()
k2.metric("Capacity Utilization", f"{util:.1%}")
k3.metric("Max Subcontracting", f"{results['Sub_Units'].max():,.0f}")
k4.metric("Total Operational Cost", f"${results['Total_Cost'].sum():,.0f}")

st.markdown("---")

# Charts Row 1
c1, c2 = st.columns(2)
with c1:
    st.subheader("Demand vs. Base Capacity")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=results['Month'], y=results['Demand'], name="Demand", line=dict(color='#1e3a8a', width=3)))
    fig.add_trace(go.Bar(x=results['Month'], y=results['Base_Cap'], name="Base Capacity", marker_color='#bfdbfe'))
    fig.update_layout(template="plotly_white", hovermode="x unified", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.subheader("Inventory & Warehouse Capacity")
    fig = px.bar(results, x='Month', y='Ending_Inv', color_discrete_sequence=['#3b82f6'])
    fig.add_hline(y=20000, line_dash="dash", line_color="red", annotation_text="Storage Limit")
    fig.update_layout(template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

# Charts Row 2
c3, c4 = st.columns(2)
with c3:
    st.subheader("Fulfillment Mix (OT vs Subcontract)")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=results['Month'], y=results['OT_Units'], name="Overtime", marker_color='#1d4ed8'))
    fig.add_trace(go.Bar(x=results['Month'], y=results['Sub_Units'], name="Subcontract", marker_color='#60a5fa'))
    fig.update_layout(barmode='stack', template="plotly_white")
    st.plotly_chart(fig, use_container_width=True)

with c4:
    st.subheader("Segment Demand Breakdown")
    fig = px.area(df_seg.head(12), x='Month', y=['Consumer', 'PC', 'Professional'], 
                  color_discrete_sequence=['#1e3a8a', '#3b82f6', '#93c5fd'])
    fig.update_layout(template="plotly_white", legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)

# Comparison & Insights
st.markdown("---")
st.subheader("Strategic Comparison (Scenario Benchmarking)")

all_strats = ["Chase (Overtime Priority)", "Level Production", "Subcontract Heavy", "Hybrid"]
comp_data = []
for s in all_strats:
    res_s = run_simulation(multiplier, s, h_cost_pct, ot_mult, sub_mult, inc_sunday)
    comp_data.append({
        "Strategy": s,
        "Total Cost": res_s['Total_Cost'].sum(),
        "Max Inventory": res_s['Ending_Inv'].max(),
        "Total OT Units": res_s['OT_Units'].sum(),
        "Total Subcontracted": res_s['Sub_Units'].sum()
    })

comp_df = pd.DataFrame(comp_data)
st.dataframe(comp_df.style.highlight_min(subset=['Total Cost'], color='#bbf7d0').format({"Total Cost": "${:,.0f}"}))

# Auto-Insights
st.markdown("### 💡 Strategy Insights")
bottlenecks = results[results['Sub_Units'] > 0]['Month'].tolist()
best_strat = comp_df.loc[comp_df['Total Cost'].idxmin(), 'Strategy']

i1, i2 = st.columns(2)
with i1:
    st.info(f"**Bottleneck Alert:** Subcontracting is required in **{', '.join(bottlenecks) if bottlenecks else 'None'}** to meet demand.")
with i2:
    st.success(f"**Best Move:** The **{best_strat}** strategy yields the lowest cost under the {scenario_name} scenario.")

st.caption("Developed by Senior Ops Analytics Team | Ref: OATY 3.0 Case Study")
