# ==============================================================================
# WHAT IS THIS IN THE CODE:
# ------------------------------------------------------------------------------
# THIS IS THE "OATY 3.0 OPERATIONS ANALYTICS DASHBOARD" (LEVEL 5 CASE STUDY).
# IT SOLVES THE CAPACITY PLANNING PROBLEM USING DATA FROM APPENDIX 1.3 & 1.5.
# IT CALCULATES THE OPTIMAL STRATEGY (CHASE, LEVEL, OR HYBRID) TO MINIMIZE 
# TOTAL COSTS (BASE + OVERTIME + SUBCONTRACT + HOLDING).
#
# KEY FEATURES:
# 1. READS DATA INTERNALLY (NO UPLOAD NEEDED).
# 2. MATCHES EXCEL LOGIC (OT LIMITS = 7425 UNITS/WK, SUNDAY = 3300 UNITS/WK).
# 3. HIGHLIGHTS "TOTAL COST" IN DARK BOLD COLORS (TARGET ~972k).
# ==============================================================================

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. SETUP & STYLING (WHITE BACKGROUND, DARK BOLD TEXT)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Operations Analytics", layout="wide")

st.markdown("""
    <style>
    /* 1. Global Background - White */
    .stApp {
        background-color: #ffffff;
        color: #000000;
        font-family: 'Arial', sans-serif;
    }

    /* 2. Headings - Dark Blue/Black */
    h1, h2, h3 {
        color: #0f172a !important; 
        font-weight: 800;
    }

    /* 3. METRIC CARDS - MAKE "TOTAL COST" AMAZING */
    div[data-testid="stMetric"] {
        background-color: #f8fafc;
        border: 2px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    /* The Label (e.g., "Total Cost") */
    div[data-testid="stMetricLabel"] {
        font-size: 16px !important;
        color: #64748b !important;
        font-weight: 600;
    }

    /* The Value (e.g., "$972,969") - DARK & BOLD */
    div[data-testid="stMetricValue"] {
        color: #000000 !important; /* Pure Black */
        font-size: 36px !important;
        font-weight: 900 !important; /* Extra Bold */
        text-shadow: 0px 0px 1px rgba(0,0,0,0.1);
    }

    /* 4. Tables */
    thead tr th {
        background-color: #f1f5f9 !important;
        color: #000000 !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE (VIABLE MODEL ACCORDING TO EXCEL)
# -----------------------------------------------------------------------------
@st.cache_data
def load_case_data():
    """
    Reconstructs the Exact Data from OATY 3.0 Case Exhibits.
    """
    # Appendix 1.5: Volume Planning
    # Note: Production Weeks vary (Jan=4, Feb=3, May=5...)
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Prod_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Sales_Weeks": [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        "Demand_Total": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    })
    
    # Constants from Inputs & Assumptions Snippet
    CONSTANTS = {
        "Base_Cap_Weekly": 16500,       # Base Capacity (5 days)
        # OT Logic derived from Overtime Model.csv Snippet:
        # Jan (4 wks): Base=66k. Max OT w/o Sun=29700. 
        # 29700/4 = 7425 units/wk (45% of Base).
        "OT_Limit_Weekly": 7425,        
        # Jan (4 wks): Max OT w/ Sun=42900. Diff=13200. 
        # 13200/4 = 3300 units/wk (20% of Base).
        "Sun_Limit_Weekly": 3300,
        "Warehouse_Cap": 20000,
        "Cost_Base": 1.0,
        "Cost_OT_Std": 1.5,
        "Cost_OT_Sun": 2.0,
        "Cost_Sub": 1.25,
        "Cost_Hold_Annual": 0.20        # 20% per annum
    }
    return df, CONSTANTS

df_case, C = load_case_data()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.header("🕹️ Strategy Controls")
st.sidebar.markdown("---")

# Scenarios
scenario = st.sidebar.selectbox("Demand Scenario", ["Base Forecast (Case)", "Peak (+15%)", "Slow (-15%)"])
d_mult = 1.15 if "Peak" in scenario else (0.85 if "Slow" in scenario else 1.0)

# Strategy
# "Chase" logic matches the 'Overtime Model.csv' snippet behavior
strategy = st.sidebar.selectbox("Fulfillment Strategy", [
    "Chase Demand (OT + Subcontract)",
    "Level Production (Build Inventory)",
    "Subcontract Heavy (Zero OT)",
    "Hybrid (Balanced)"
])

st.sidebar.markdown("### 💰 Cost Parameters")
h_cost = st.sidebar.slider("Annual Holding Cost %", 10, 30, int(C['Cost_Hold_Annual']*100)) / 100.0
ot_rate = st.sidebar.number_input("Overtime Rate", 1.0, 2.5, C['Cost_OT_Std'])
sub_rate = st.sidebar.number_input("Subcontract Rate", 1.0, 2.0, C['Cost_Sub'])
sunday = st.sidebar.checkbox("Enable Sunday OT", value=False)

# -----------------------------------------------------------------------------
# 4. ANALYTICS ENGINE (THE CALCULATOR)
# -----------------------------------------------------------------------------
def run_simulation(dem_m, strat, hc, ot_r, sub_r, sun_on):
    df = df_case.copy()
    
    # 1. Setup Monthly Demands & Capacities
    df['Demand'] = df['Demand_Total'] * dem_m
    df['Cap_Base'] = df['Prod_Weeks'] * C['Base_Cap_Weekly']
    
    # OT Capacity Calculation
    ot_limit = C['OT_Limit_Weekly']
    if sun_on: ot_limit += C['Sun_Limit_Weekly']
    df['Cap_Max_OT'] = df['Prod_Weeks'] * ot_limit
    
    # 2. Iterate Months (Continuity of Inventory)
    prod, ot, sub, inv = [], [], [], [0]
    curr_inv = 0
    
    # Level Prod Target: Total Demand / Total Weeks
    total_d = df['Demand'].sum()
    total_w = df['Prod_Weeks'].sum()
    level_rate = total_d / total_w
    
    for i, row in df.iterrows():
        d = row['Demand']
        base = row['Cap_Base']
        max_ot = row['Cap_Max_OT']
        w = row['Prod_Weeks']
        
        p, o, s = 0, 0, 0 # Standard, OT, Subcontract units
        
        if strat == "Chase Demand (OT + Subcontract)":
            # 1. Use Inventory first
            net_req = d - curr_inv
            
            # 2. Use Base Production (up to Base Cap or Net Req)
            # Actually, standard Chase usually maxes Base first to avoid idle labor
            p = base # Assume we pay for base capacity regardless (Factory Loading)
            
            remaining = net_req - p
            
            if remaining > 0:
                # 3. Use Overtime
                o = min(remaining, max_ot)
                # 4. Use Subcontract
                s = max(0, remaining - o)
                curr_inv = 0
            else:
                # Surplus goes to inventory
                curr_inv = -remaining # (p + curr_inv - d)

        elif strat == "Level Production (Build Inventory)":
            target = level_rate * w
            # Produce Target (Split into Base + OT + Sub)
            # Fill Base
            p = min(target, base)
            rem_target = target - p
            # Fill OT
            if rem_target > 0:
                o = min(rem_target, max_ot)
                rem_target -= o
            # Fill Sub
            if rem_target > 0:
                s = rem_target
                
            # Inventory Check
            ending = curr_inv + p + o + s - d
            if ending < 0:
                # Shortage! Must Subcontract the gap
                s += abs(ending)
                curr_inv = 0
            else:
                curr_inv = ending
                
        elif strat == "Subcontract Heavy (Zero OT)":
            p = base
            net = d - curr_inv - p
            if net > 0:
                s = net
                curr_inv = 0
            else:
                curr_inv = abs(net)
                
        else: # Hybrid
            p = base
            net = d - curr_inv - p
            if net > 0:
                # Use 50% OT Capacity
                o = min(net, max_ot * 0.5)
                s = max(0, net - o)
                curr_inv = 0
            else:
                curr_inv = abs(net)
                
        prod.append(p); ot.append(o); sub.append(s); inv.append(curr_inv)
        
    df['Prod_Std'] = prod
    df['Prod_OT'] = ot
    df['Prod_Sub'] = sub
    df['End_Inv'] = inv[1:]
    
    # 3. Financials
    # Base Cost usually sunk, but for comparison we price it at 1.0
    df['$ Base'] = df['Prod_Std'] * 1.0
    df['$ OT'] = df['Prod_OT'] * ot_r
    df['$ Sub'] = df['Prod_Sub'] * sub_r
    # Holding Cost: Monthly Rate * Ending Inventory
    df['$ Hold'] = df['End_Inv'] * (hc / 12)
    
    df['Total Cost'] = df['$ Base'] + df['$ OT'] + df['$ Sub'] + df['$ Hold']
    
    return df

res = run_simulation(d_mult, strategy, h_cost, ot_rate, sub_rate, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("OATY 3.0 OPERATIONS DASHBOARD")
st.markdown("### 📊 Strategic Analysis & Cost Modeling")

# --- SECTION A: THE BIG NUMBERS ---
# This is where 972969 (or similar viable Excel numbers) will appear
total_c = res['Total Cost'].sum()
avg_inv = res['End_Inv'].mean()
max_sub = res['Prod_Sub'].max()
util_rate = (res['Prod_Std'].sum() + res['Prod_OT'].sum()) / (res['Cap_Base'].sum() + res['Cap_Max_OT'].sum())

col1, col2, col3, col4 = st.columns(4)
col1.metric("TOTAL ESTIMATED COST", f"${total_c:,.0f}", delta="Target Optimization")
col2.metric("Avg Inventory Levels", f"{avg_inv:,.0f} units")
col3.metric("Capacity Utilization", f"{util_rate:.1%}")
col4.metric("Peak Subcontracting", f"{max_sub:,.0f} units")

st.markdown("---")

# --- SECTION B: VISUALS ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Aggregate Production Plan")
    # Stacked Bar Chart
    fig = go.Figure()
    fig.add_trace(go.Bar(x=res['Month'], y=res['Prod_Std'], name='Standard Prod', marker_color='#cbd5e1')) # Light Grey
    fig.add_trace(go.Bar(x=res['Month'], y=res['Prod_OT'], name='Overtime', marker_color='#334155')) # Dark Slate
    fig.add_trace(go.Bar(x=res['Month'], y=res['Prod_Sub'], name='Subcontract', marker_color='#000000')) # Black
    
    # Demand Line
    fig.add_trace(go.Scatter(x=res['Month'], y=res['Demand'], name='Demand', 
                             line=dict(color='#dc2626', width=4))) # Red
    
    fig.update_layout(barmode='stack', template='plotly_white', height=400, 
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with c2:
    st.subheader("Inventory Monitor")
    fig2 = px.area(res, x='Month', y='End_Inv', title="Warehouse Utilization",
                   color_discrete_sequence=['#475569'])
    fig2.add_hline(y=20000, line_dash="dash", line_color="red", annotation_text="Max 20k")
    fig2.update_layout(template='plotly_white', height=400)
    st.plotly_chart(fig2, use_container_width=True)

# --- SECTION C: STRATEGY COMPARISON ---
st.markdown("---")
st.subheader("🏆 Strategy Benchmarking (Viable Cost Model)")

cols = st.columns(1)
# Calculate all strategies for the table
strats = ["Chase Demand (OT + Subcontract)", "Level Production (Build Inventory)", "Subcontract Heavy (Zero OT)", "Hybrid (Balanced)"]
rows = []
for s in strats:
    r = run_simulation(d_mult, s, h_cost, ot_rate, sub_rate, sunday)
    rows.append({
        "Strategy": s,
        "Total Cost": r['Total Cost'].sum(),
        "OT Units": r['Prod_OT'].sum(),
        "Subcontract Units": r['Prod_Sub'].sum(),
        "Max Inventory": r['End_Inv'].max()
    })

comp_df = pd.DataFrame(rows).set_index("Strategy")
st.dataframe(comp_df.style.format({"Total Cost": "${:,.0f}", "OT Units": "{:,.0f}", "Subcontract Units": "{:,.0f}", "Max Inventory": "{:,.0f}"})
             .background_gradient(subset=["Total Cost"], cmap="Greys"), use_container_width=True)

# Recommendation
best = comp_df['Total Cost'].idxmin()
st.success(f"**OPTIMAL STRATEGY:** {best} offers the lowest cost structure for the {scenario} scenario.")
