import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

# -----------------------------------------------------------------------------
# 1. SETUP & STYLING (CLEAN PROFESSIONAL THEME)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Operations Dashboard", layout="wide")

# Force High-Contrast Professional Styling (No Emojis, Dark Text on White)
st.markdown("""
    <style>
    /* Main Background and Text */
    .stApp {
        background-color: #ffffff;
        color: #333333;
    }
    
    /* Headings - Dark Corporate Blue */
    h1, h2, h3, h4 {
        color: #1e3a8a !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        padding: 15px;
        border-radius: 5px;
        border-left: 5px solid #1e3a8a;
    }
    div[data-testid="stMetricLabel"] {
        color: #666666 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #1e3a8a !important;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #f1f5f9;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] label {
        color: #1e3a8a !important;
    }
    
    /* Table Styling */
    thead tr th:first-child { display:none }
    tbody th { display:none }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE (INTERNAL GENERATION)
# -----------------------------------------------------------------------------
def ensure_data_exists():
    """
    Internally generates the exact data from Case Exhibits 1.3 and 1.5
    to ensure the dashboard runs without external file dependencies.
    """
    # Exhibit 1.5: Volume Planning Data
    data_vol = {
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Production_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Sales_Weeks":      [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        "Avg_Weekly_Demand":[17880, 18860, 18700, 19600, 17150, 15000, 15000, 15000, 15500, 16500, 17000, 24000],
        "Total_Demand":     [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    }
    
    # Exhibit 1.3: Segment Mix
    data_seg = {
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Consumer": [5960, 6090, 6030, 6540, 5800, 5000, 5000, 5000, 5000, 5500, 5600, 8000],
        "PC":       [8940, 9550, 9510, 9770, 8450, 7500, 7500, 7500, 8000, 8200, 8500, 12000],
        "Professional": [2980, 3220, 3160, 3290, 2900, 2500, 2500, 2500, 2500, 2800, 2900, 4000]
    }

    # Case Inputs & Assumptions
    data_inp = {
        "Parameter": ["Weekly Base Capacity", "Weekday+Sat OT Limit (Units/Wk)", "Sunday OT Limit (Units/Wk)", 
                      "Holding Cost (Annual %)", "OT Cost Multiplier (Weekday)", "OT Cost Multiplier (Sunday)", 
                      "Subcontract Cost Multiplier", "Warehouse Capacity"],
        "Value": [16500, 7425, 3300, 0.20, 1.5, 2.0, 1.25, 20000]
    }

    df_vol = pd.DataFrame(data_vol)
    df_seg = pd.DataFrame(data_seg)
    df_inp = pd.DataFrame(data_inp)

    # Create Excel in memory/disk for processing
    with pd.ExcelWriter('OATY_Aadit.xlsx', engine='openpyxl') as writer:
        df_vol.to_excel(writer, sheet_name='Volume_Planning', index=False)
        df_seg.to_excel(writer, sheet_name='Segment_Mix', index=False)
        df_inp.to_excel(writer, sheet_name='Inputs', index=False)

@st.cache_data
def load_data():
    ensure_data_exists()
    xls = pd.ExcelFile('OATY_Aadit.xlsx')
    df_vol = pd.read_excel(xls, 'Volume_Planning')
    df_seg = pd.read_excel(xls, 'Segment_Mix')
    df_inp = pd.read_excel(xls, 'Inputs')
    
    const = dict(zip(df_inp['Parameter'], df_inp['Value']))
    return df_vol, df_seg, const

# Load Data
try:
    df_vol, df_seg, CONSTANTS = load_data()
except Exception as e:
    st.error(f"Critical Data Error: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.title("Operations Control")
st.sidebar.markdown("---")

# Scenario Logic
scenario = st.sidebar.selectbox("Demand Scenario", ["Base Forecast", "Boom (+15%)", "Slump (-15%)"])
d_mult = 1.15 if "Boom" in scenario else (0.85 if "Slump" in scenario else 1.0)

# Strategy Logic
strategy = st.sidebar.selectbox("Operational Strategy", [
    "Chase (Prioritize OT)", 
    "Level Production (Inventory Focus)", 
    "Subcontract Heavy", 
    "Hybrid (Balanced Approach)"
])

st.sidebar.markdown("---")
st.sidebar.subheader("Financial Levers")
h_cost = st.sidebar.slider("Annual Holding Cost %", 10, 40, 20) / 100.0
ot_mult = st.sidebar.number_input("Overtime Multiplier", 1.0, 3.0, 1.5, 0.1)
sub_mult = st.sidebar.number_input("Subcontract Multiplier", 1.0, 3.0, 1.25, 0.05)
sunday = st.sidebar.checkbox("Allow Sunday OT (2.0x)", value=False)

# -----------------------------------------------------------------------------
# 4. ANALYTICS SIMULATION ENGINE
# -----------------------------------------------------------------------------
def run_analytics(df_v, dem_m, strat, hc, ot_m, sub_m, sun_ok):
    df = df_v.copy()
    
    # 1. Demand & Capacity
    df['Demand'] = df['Total_Demand'] * dem_m
    df['Base_Cap'] = df['Production_Weeks'] * CONSTANTS['Weekly Base Capacity']
    
    # OT Limit Calculation
    ot_limit_wk = CONSTANTS['Weekday+Sat OT Limit (Units/Wk)']
    if sun_ok: ot_limit_wk += CONSTANTS['Sunday OT Limit (Units/Wk)']
    df['Max_OT'] = df['Production_Weeks'] * ot_limit_wk

    # 2. Strategy Execution
    prod, ot, sub, inv = [], [], [], [0]
    curr_inv = 0
    
    # Level Target: Total Demand / Total Production Weeks
    level_daily_rate = df['Demand'].sum() / df['Production_Weeks'].sum()

    for i, row in df.iterrows():
        dem = row['Demand']
        cap = row['Base_Cap']
        max_o = row['Max_OT']
        weeks = row['Production_Weeks']
        
        p, o, s = 0, 0, 0 # Standard, OT, Subcontract
        
        if strat == "Chase (Prioritize OT)":
            p = cap
            gap = dem - p - curr_inv
            if gap > 0:
                o = min(gap, max_o)
                s = max(0, gap - o)
                curr_inv = 0
            else:
                curr_inv = abs(gap)
                
        elif strat == "Level Production (Inventory Focus)":
            target = level_daily_rate * weeks
            p = min(target, cap)
            remainder = target - p
            
            # If target > cap, use OT
            if remainder > 0:
                o = min(remainder, max_o)
                s = max(0, remainder - o)
            
            # Recalculate Inventory to see if we are short
            projected_inv = curr_inv + p + o + s - dem
            if projected_inv < 0:
                s += abs(projected_inv) # Emergency Subcontract
                curr_inv = 0
            else:
                curr_inv = projected_inv

        elif strat == "Subcontract Heavy":
            p = cap
            gap = dem - p - curr_inv
            if gap > 0:
                s = gap
                curr_inv = 0
            else:
                curr_inv = abs(gap)
        
        else: # Hybrid
            p = cap
            gap = dem - p - curr_inv
            if gap > 0:
                o = min(gap, max_o * 0.5) # Use only 50% OT
                s = max(0, gap - o)
                curr_inv = 0
            else:
                curr_inv = abs(gap)

        prod.append(p); ot.append(o); sub.append(s); inv.append(curr_inv)

    df['Prod_Std'] = prod
    df['Prod_OT'] = ot
    df['Prod_Sub'] = sub
    df['Ending_Inv'] = inv[1:]
    
    # 3. Financials
    df['Cost_Base'] = df['Prod_Std'] * 1.0
    df['Cost_OT'] = df['Prod_OT'] * ot_m
    df['Cost_Sub'] = df['Prod_Sub'] * sub_m
    df['Cost_Hold'] = df['Ending_Inv'] * (hc / 12)
    df['Total_Cost'] = df['Cost_Base'] + df['Cost_OT'] + df['Cost_Sub'] + df['Cost_Hold']
    
    return df

results = run_analytics(df_vol, d_mult, strategy, h_cost, ot_mult, sub_mult, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD VISUALIZATION
# -----------------------------------------------------------------------------
st.title("OATY 3.0: Strategic Operations Dashboard")
st.markdown(f"**View:** {scenario} | **Mode:** {strategy}")

# --- KPI Cards ---
k1, k2, k3, k4 = st.columns(4)
total_c = results['Total_Cost'].sum()
avg_inv = results['Ending_Inv'].mean()
max_sub = results['Prod_Sub'].max()
util = (results['Prod_Std'].sum() + results['Prod_OT'].sum()) / (results['Base_Cap'].sum() + results['Max_OT'].sum())

k1.metric("Est. Total Cost", f"${total_c:,.0f}", delta="Annual")
k2.metric("Avg Inventory", f"{avg_inv:,.0f}", help="Average monthly ending inventory")
k3.metric("Capacity Utilization", f"{util:.1%}", help="Includes Standard + OT")
k4.metric("Peak Outsourcing", f"{max_sub:,.0f}", help="Max units subcontracted in a single month")

# --- Aggregate Production Planning Graph ---
st.markdown("### Aggregate Production Plan")
fig_main = go.Figure()
fig_main.add_trace(go.Bar(x=results['Month'], y=results['Prod_Std'], name='Regular Cap', marker_color='#93c5fd'))
fig_main.add_trace(go.Bar(x=results['Month'], y=results['Prod_OT'], name='Overtime', marker_color='#2563eb'))
fig_main.add_trace(go.Bar(x=results['Month'], y=results['Prod_Sub'], name='Subcontract', marker_color='#f59e0b'))
fig_main.add_trace(go.Scatter(x=results['Month'], y=results['Demand'], name='Demand', line=dict(color='#1e3a8a', width=4)))

fig_main.update_layout(barmode='stack', template='plotly_white', height=450, 
                      legend=dict(orientation="h", y=1.1))
st.plotly_chart(fig_main, use_container_width=True)
st.caption("")

# --- Comparison & Analysis ---
c1, c2 = st.columns(2)

with c1:
    st.subheader("Inventory vs. Warehouse Limit")
    fig_inv = px.area(results, x='Month', y='Ending_Inv', title="Inventory Levels", color_discrete_sequence=['#10b981'])
    fig_inv.add_hline(y=CONSTANTS['Warehouse Capacity'], line_dash="dash", line_color="red", annotation_text="Limit (20k)")
    fig_inv.update_layout(template='plotly_white')
    st.plotly_chart(fig_inv, use_container_width=True)

with c2:
    st.subheader("Strategy Benchmarking")
    # Live Comparison
    strats = ["Chase (Prioritize OT)", "Level Production (Inventory Focus)", "Subcontract Heavy", "Hybrid (Balanced Approach)"]
    comp_res = []
    for s in strats:
        r = run_analytics(df_vol, d_mult, s, h_cost, ot_mult, sub_mult, sunday)
        comp_res.append({"Strategy": s, "Cost": r['Total_Cost'].sum(), "Max Inv": r['Ending_Inv'].max()})
    
    df_comp = pd.DataFrame(comp_res).set_index("Strategy")
    st.dataframe(df_comp.style.format({"Cost": "${:,.0f}", "Max Inv": "{:,.0f}"}), use_container_width=True)

# --- Automated Insights ---
st.markdown("---")
best_strat = df_comp['Cost'].idxmin()
st.info(f"Recommendation: Based on current parameters, '{best_strat}' is the optimal strategy.")
