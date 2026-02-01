# ==============================================================================
# OATY 3.0 OPERATIONS DASHBOARD - HIGH CONTRAST VIABLE MODEL
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. SETUP & HIGH CONTRAST STYLING (BLACK & WHITE ONLY)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Viable Model", layout="wide")

st.markdown("""
    <style>
    /* GLOBAL RESET - FORCE BLACK AND WHITE */
    .stApp {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-family: 'Arial', sans-serif;
    }

    /* HEADINGS */
    h1, h2, h3, h4, h5, h6 {
        color: #000000 !important;
        font-weight: 900 !important; /* Extra Bold */
        text-transform: uppercase;
    }

    /* METRIC CARDS - HIGH VISIBILITY BORDERS */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #000000 !important;
        border-radius: 0px !important; /* Square corners for professional look */
        padding: 15px !important;
        box-shadow: none !important;
    }

    div[data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-size: 16px !important;
        font-weight: bold !important;
        text-decoration: underline;
    }

    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-size: 30px !important;
        font-weight: 900 !important;
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #f0f0f0 !important; /* Light Grey for contrast */
        border-right: 2px solid #000000;
    }
    
    /* DATAFRAME/TABLES */
    div[data-testid="stDataFrame"] {
        border: 2px solid #000000;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE (INTERNAL - NO UPLOAD NEEDED)
# -----------------------------------------------------------------------------
@st.cache_data
def get_case_data():
    # Appendix 1.5: Volume Planning
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Prod_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Sales_Weeks": [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        "Demand": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    })
    
    # Constants from Case Snippets
    CONSTANTS = {
        "Base_Cap_Wk": 16500,
        "OT_Limit_Wk": 7425, # 45% of Base
        "Sun_Limit_Wk": 3300, # 20% of Base
        "Whse_Cap": 20000
    }
    return df, CONSTANTS

df_case, C = get_case_data()

# -----------------------------------------------------------------------------
# 3. CONTROLS (SIDEBAR)
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🛠 OPERATIONS CONTROLS")
st.sidebar.markdown("---")

scenario = st.sidebar.selectbox("DEMAND SCENARIO", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
d_mult = 1.15 if "Peak" in scenario else (0.85 if "Slow" in scenario else 1.0)

strategy = st.sidebar.selectbox("STRATEGY SELECTION", [
    "Chase (Prioritize OT)", 
    "Level Production", 
    "Subcontract Heavy", 
    "Hybrid"
])

st.sidebar.markdown("---")
st.sidebar.markdown("### COST SETTINGS")
h_cost = st.sidebar.slider("HOLDING COST %", 10, 30, 20) / 100.0
ot_rate = st.sidebar.number_input("OT MULTIPLIER", 1.0, 2.5, 1.5)
sub_rate = st.sidebar.number_input("SUBCONTRACT MULTIPLIER", 1.0, 2.0, 1.25)
sunday = st.sidebar.checkbox("ENABLE SUNDAY SHIFTS", value=True)

# -----------------------------------------------------------------------------
# 4. ANALYTICS ENGINE
# -----------------------------------------------------------------------------
def run_model(dm, strat, hc, otr, subr, sun):
    df = df_case.copy()
    df['Adj_Demand'] = df['Demand'] * dm
    df['Base_Cap'] = df['Prod_Weeks'] * C['Base_Cap_Wk']
    
    ot_lim = C['OT_Limit_Wk'] + (C['Sun_Limit_Wk'] if sun else 0)
    df['Max_OT'] = df['Prod_Weeks'] * ot_lim
    
    prod, ot, sub, inv = [], [], [], [0]
    curr = 0
    level_target = df['Adj_Demand'].sum() / df['Prod_Weeks'].sum()
    
    for i, row in df.iterrows():
        d = row['Adj_Demand']
        base = row['Base_Cap']
        mx_ot = row['Max_OT']
        w = row['Prod_Weeks']
        
        p, o, s = 0, 0, 0
        
        if strat == "Chase (Prioritize OT)":
            p = base
            net = d - curr - p
            if net > 0:
                o = min(net, mx_ot)
                s = max(0, net - o)
                curr = 0
            else:
                curr = abs(net)
                
        elif strat == "Level Production":
            tgt = level_target * w
            p = min(tgt, base)
            rem = tgt - p
            if rem > 0:
                o = min(rem, mx_ot)
                rem -= o
            if rem > 0:
                s = rem
            
            end = curr + p + o + s - d
            if end < 0:
                s += abs(end)
                curr = 0
            else:
                curr = end

        elif strat == "Subcontract Heavy":
            p = base
            net = d - curr - p
            if net > 0:
                s = net
                curr = 0
            else:
                curr = abs(net)
        
        else: # Hybrid
            p = base
            net = d - curr - p
            if net > 0:
                o = min(net, mx_ot * 0.5)
                s = max(0, net - o)
                curr = 0
            else:
                curr = abs(net)

        prod.append(p); ot.append(o); sub.append(s); inv.append(curr)

    df['Std_Units'] = prod
    df['OT_Units'] = ot
    df['Sub_Units'] = sub
    df['End_Inv'] = inv[1:]
    
    # Financials
    df['Cost_Base'] = df['Std_Units'] * 1.0
    df['Cost_OT'] = df['OT_Units'] * otr
    df['Cost_Sub'] = df['Sub_Units'] * subr
    df['Cost_Hold'] = df['End_Inv'] * (hc/12)
    df['Total_Cost'] = df['Cost_Base'] + df['Cost_OT'] + df['Cost_Sub'] + df['Cost_Hold']
    
    return df

res = run_model(d_mult, strategy, h_cost, ot_rate, sub_rate, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT (MONOCHROME VISUALS)
# -----------------------------------------------------------------------------
st.title("OATY 3.0 OPERATIONS DASHBOARD")
st.markdown("### VIABLE COST MODEL (BLACK & WHITE MODE)")

# KPI SECTION
tc = res['Total_Cost'].sum()
avg_i = res['End_Inv'].mean()
mx_s = res['Sub_Units'].max()
util = (res['Std_Units'].sum() + res['OT_Units'].sum()) / (res['Base_Cap'].sum() + res['Max_OT'].sum())

c1, c2, c3, c4 = st.columns(4)
c1.metric("TOTAL COST (TARGET)", f"${tc:,.0f}")
c2.metric("AVG INVENTORY", f"{avg_i:,.0f}")
c3.metric("UTILIZATION", f"{util:.1%}")
c4.metric("PEAK SUBCONTRACT", f"{mx_s:,.0f}")

st.markdown("---")

# CHARTS SECTION - GREYSCALE
g1, g2 = st.columns([2, 1])

with g1:
    st.markdown("#### PRODUCTION MIX vs DEMAND")
    fig = go.Figure()
    # Black and Grey Bars
    fig.add_trace(go.Bar(x=res['Month'], y=res['Std_Units'], name='Standard', marker_color='#808080')) # Grey
    fig.add_trace(go.Bar(x=res['Month'], y=res['OT_Units'], name='Overtime', marker_color='#404040')) # Dark Grey
    fig.add_trace(go.Bar(x=res['Month'], y=res['Sub_Units'], name='Subcontract', marker_color='#000000')) # Black
    # Dashed Line for Demand
    fig.add_trace(go.Scatter(x=res['Month'], y=res['Adj_Demand'], name='Demand', 
                             line=dict(color='black', width=3, dash='dot')))
    
    fig.update_layout(barmode='stack', template='plotly_white', height=400,
                      legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with g2:
    st.markdown("#### INVENTORY LEVELS")
    fig2 = px.area(res, x='Month', y='End_Inv')
    # Force black fill
    fig2.update_traces(line_color='black', fill='tozeroy')
    fig2.add_hline(y=20000, line_dash="dash", line_color="black", annotation_text="Limit (20k)")
    fig2.update_layout(template='plotly_white', height=400)
    st.plotly_chart(fig2, use_container_width=True)

# STRATEGY COMPARISON TABLE
st.markdown("---")
st.markdown("### 🏆 STRATEGY BENCHMARKING (VIABLE COST MODEL)")

# Calculate all 4 strategies
strats = ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"]
data_comp = []
for s in strats:
    r = run_model(d_mult, s, h_cost, ot_rate, sub_rate, sunday)
    data_comp.append({
        "STRATEGY": s,
        "TOTAL COST": r['Total_Cost'].sum(),
        "MAX INVENTORY": r['End_Inv'].max(),
        "SUBCONTRACTED": r['Sub_Units'].sum()
    })

df_comp = pd.DataFrame(data_comp).sort_values("TOTAL COST")

# Simple, High-Visibility Table (No Gradients)
st.dataframe(
    df_comp.style.format({
        "TOTAL COST": "${:,.0f}", 
        "MAX INVENTORY": "{:,.0f}",
        "SUBCONTRACTED": "{:,.0f}"
    }), 
    use_container_width=True,
    hide_index=True
)

best = df_comp.iloc[0]['STRATEGY']
low_cost = df_comp.iloc[0]['TOTAL COST']

st.info(f"**RECOMMENDATION:** The **{best}** strategy is viable with a lowest cost of **${low_cost:,.0f}**.")
