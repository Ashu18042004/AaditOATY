# ==============================================================================
# OATY 3.0 OPERATIONS DASHBOARD - FIXED & DYNAMIC
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. SETUP & HIGH VISIBILITY STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Analysis", layout="wide")

st.markdown("""
    <style>
    /* GLOBAL RESET - HIGH CONTRAST */
    .stApp {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-family: 'Arial', sans-serif !important;
    }

    /* HEADERS */
    h1, h2, h3, h4 {
        color: #000000 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* METRIC CARDS - CLEAN & SHARP */
    div[data-testid="stMetric"] {
        background-color: #f9f9f9 !important;
        border: 2px solid #000000 !important;
        padding: 15px !important;
        border-radius: 0px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #333333 !important;
        font-weight: bold !important;
        font-size: 14px !important;
    }
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 32px !important;
    }
    
    /* TABLE HEADERS */
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #333333 !important;
        color: white !important;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE
# -----------------------------------------------------------------------------
@st.cache_data
def get_clean_data():
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Prod_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Sales_Weeks": [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        "Demand": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    })
    CONSTANTS = {
        "Base_Cap_Wk": 16500.0,
        "OT_Limit_Wk": 7425.0,  
        "Sun_Limit_Wk": 3300.0, 
        "Whse_Cap": 20000.0
    }
    return df, CONSTANTS

df_case, C = get_clean_data()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🛠 MODEL INPUTS")
st.sidebar.markdown("---")

scenario = st.sidebar.selectbox("DEMAND SCENARIO", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
d_mult = 1.15 if "Peak" in scenario else (0.85 if "Slow" in scenario else 1.0)

strategy = st.sidebar.selectbox("STRATEGY", ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"])

st.sidebar.markdown("### 💰 COSTS")
h_cost = st.sidebar.slider("HOLDING COST %", 10, 30, 20) / 100.0
ot_rate = st.sidebar.number_input("OT MULTIPLIER", 1.0, 2.5, 1.5)
sub_rate = st.sidebar.number_input("SUBCONTRACT MULTIPLIER", 1.0, 2.0, 1.25)
sunday = st.sidebar.checkbox("ENABLE SUNDAY OT", value=False)

# -----------------------------------------------------------------------------
# 4. CALCULATION ENGINE
# -----------------------------------------------------------------------------
def run_model(dm, strat, hc, otr, subr, sun):
    df = df_case.copy()
    df['Adj_Demand'] = df['Demand'] * dm
    df['Base_Cap'] = df['Prod_Weeks'] * C['Base_Cap_Wk']
    
    ot_factor = C['OT_Limit_Wk'] + (C['Sun_Limit_Wk'] if sun else 0)
    df['Max_OT'] = df['Prod_Weeks'] * ot_factor
    
    prod, ot, sub, inv = [], [], [], [0]
    curr_inv = 0
    level_rate = df['Adj_Demand'].sum() / df['Prod_Weeks'].sum()

    for i, row in df.iterrows():
        d, base, mx_ot, w = row['Adj_Demand'], row['Base_Cap'], row['Max_OT'], row['Prod_Weeks']
        p, o, s = 0, 0, 0
        
        if strat == "Chase (Prioritize OT)":
            p = base
            req = d - curr_inv - p
            if req > 0:
                o = min(req, mx_ot)
                s = max(0, req - o)
                curr_inv = 0
            else:
                curr_inv = abs(req)

        elif strat == "Level Production":
            tgt = level_rate * w
            p = min(tgt, base)
            rem = tgt - p
            if rem > 0:
                o = min(rem, mx_ot)
                rem -= o
            if rem > 0: s = rem
            end = curr_inv + p + o + s - d
            if end < 0: s += abs(end); curr_inv = 0
            else: curr_inv = end

        elif strat == "Subcontract Heavy":
            p = base
            req = d - curr_inv - p
            if req > 0: s = req; curr_inv = 0
            else: curr_inv = abs(req)
        
        else: # Hybrid
            p = base
            req = d - curr_inv - p
            if req > 0:
                o = min(req, mx_ot * 0.5)
                s = max(0, req - o)
                curr_inv = 0
            else: curr_inv = abs(req)

        prod.append(p); ot.append(o); sub.append(s); inv.append(curr_inv)

    df['Std'] = prod; df['OT'] = ot; df['Sub'] = sub; df['Inv'] = inv[1:]
    
    # Financials
    df['Cost'] = (df['Std']*1.0) + (df['OT']*otr) + (df['Sub']*subr) + (df['Inv']*(hc/12))
    return df

res = run_model(d_mult, strategy, h_cost, ot_rate, sub_rate, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("OATY 3.0 OPERATIONS DASHBOARD")

# --- DYNAMIC BENCHMARKING (THINKING ENGINE) ---
# Calculate best strategy in background to give context
strats = ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"]
costs = {s: run_model(d_mult, s, h_cost, ot_rate, sub_rate, sunday)['Cost'].sum() for s in strats}
best_strat = min(costs, key=costs.get)
best_cost = costs[best_strat]
current_cost = res['Cost'].sum()
delta = current_cost - best_cost

# --- KPI CARDS ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("TOTAL COST", f"${current_cost:,.0f}", delta=f"${-delta:,.0f} vs Optimal" if delta > 0 else "Optimal Choice", delta_color="inverse")
k2.metric("AVG INVENTORY", f"{res['Inv'].mean():,.0f}")
util = (res['Std'].sum() + res['OT'].sum()) / (res['Base_Cap'].sum() + res['Max_OT'].sum())
k3.metric("UTILIZATION", f"{util:.1%}")
k4.metric("OPTIMAL STRATEGY", best_strat.split(" ")[0].upper())

st.markdown("---")

# --- VISIBILITY FIX: CHARTS ---
c1, c2 = st.columns([2, 1])

with c1:
    st.markdown("#### PRODUCTION MIX vs DEMAND")
    fig = go.Figure()
    
    # 1. Standard (Light Grey)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['Std'], name='Standard (1.0x)',
        marker_color='#d9d9d9', marker_line_color='black', marker_line_width=1
    ))
    # 2. Overtime (Dark Grey)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['OT'], name=f'Overtime ({ot_rate}x)',
        marker_color='#737373', marker_line_color='black', marker_line_width=1
    ))
    # 3. Subcontract (Black)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['Sub'], name=f'Subcontract ({sub_rate}x)',
        marker_color='#000000', marker_line_color='black', marker_line_width=1
    ))
    # 4. Demand (Line)
    fig.add_trace(go.Scatter(
        x=res['Month'], y=res['Adj_Demand'], name='Demand',
        line=dict(color='black', width=4, dash='solid')
    ))
    
    fig.update_layout(
        barmode='stack', 
        template='plotly_white', 
        height=450,
        legend=dict(orientation="h", y=1.1),
        font=dict(family="Arial", size=12, color="black"),
        hovermode="x unified" # Adds dynamic tooltips
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with c2:
    st.markdown("#### INVENTORY LEVELS")
    fig2 = px.area(res, x='Month', y='Inv')
    # FIX: Use 'fillcolor' (no underscore) and line_color
    fig2.update_traces(line_color='black', fillcolor='rgba(0,0,0,0.2)')
    
    # Add Warehouse Limit Line
    fig2.add_hline(y=20000, line_dash="dash", line_color="black", annotation_text="Limit (20k)")
    
    fig2.update_layout(
        template='plotly_white', 
        height=450,
        font=dict(family="Arial", size=12, color="black"),
        yaxis_title="Units"
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- TABLE ---
st.markdown("---")
st.markdown("#### STRATEGY COMPARISON")

# Create comparison dataframe
df_comp = pd.DataFrame([
    {"STRATEGY": s, "COST": c, "DIFF": c - best_cost} 
    for s, c in costs.items()
]).sort_values("COST")

st.dataframe(
    df_comp.style.format({"COST": "${:,.0f}", "DIFF": "+${:,.0f}"}),
    use_container_width=True,
    hide_index=True
)
