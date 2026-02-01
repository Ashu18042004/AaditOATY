# ==============================================================================
# OATY 3.0 OPERATIONS DASHBOARD - BLUE THEME & HIGH VISIBILITY
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. VISUAL SETUP (BLUE THEME + READABILITY)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Dashboard", layout="wide")

st.markdown("""
    <style>
    /* 1. Main Background */
    .stApp {
        background-color: #f8faff !important; /* Very Light Blue-Grey */
        color: #000000 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    /* 2. Headers - Navy Blue & Visible */
    h1, h2, h3, h4, label {
        color: #1e3a8a !important; /* Navy Blue */
        font-weight: 800 !important;
        text-transform: uppercase;
    }
    
    /* 3. Metric Cards - Professional Look */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 1px solid #bfdbfe !important; /* Light Blue Border */
        border-left: 5px solid #1e3a8a !important; /* Thick Blue Accent */
        box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important;
        border-radius: 8px !important;
        padding: 15px !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #475569 !important; /* Slate Grey */
        font-weight: bold !important;
        font-size: 15px !important;
    }
    div[data-testid="stMetricValue"] {
        color: #1e3a8a !important; /* Navy Blue */
        font-weight: 900 !important;
        font-size: 32px !important;
    }

    /* 4. Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #eff6ff !important; /* Light Blue Sidebar */
        border-right: 1px solid #dbeafe;
    }
    
    /* 5. Tables - Readable */
    thead tr th {
        background-color: #1e3a8a !important;
        color: white !important;
        font-size: 14px !important;
    }
    tbody tr td {
        color: #000000 !important;
        font-weight: 500 !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE
# -----------------------------------------------------------------------------
@st.cache_data
def get_data():
    # Appendix 1.5 Data
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Prod_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Demand": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    })
    # Case Constants
    CONSTANTS = {
        "Base_Cap_Wk": 16500.0,
        "OT_Limit_Wk": 7425.0,  
        "Sun_Limit_Wk": 3300.0, 
        "Whse_Cap": 20000.0
    }
    return df, CONSTANTS

df_case, C = get_data()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ SETTINGS")
st.sidebar.markdown("---")

scenario = st.sidebar.selectbox("DEMAND SCENARIO", ["Base Forecast", "Peak (+15%)", "Slow (-15%)"])
d_mult = 1.15 if "Peak" in scenario else (0.85 if "Slow" in scenario else 1.0)

strategy = st.sidebar.selectbox("STRATEGY", ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"])

st.sidebar.markdown("### 💰 COST INPUTS")
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
    
    ot_fac = C['OT_Limit_Wk'] + (C['Sun_Limit_Wk'] if sun else 0)
    df['Max_OT'] = df['Prod_Weeks'] * ot_fac
    
    prod, ot, sub, inv = [], [], [], [0]
    curr = 0
    level_rate = df['Adj_Demand'].sum() / df['Prod_Weeks'].sum()

    for i, row in df.iterrows():
        d, base, mx_ot, w = row['Adj_Demand'], row['Base_Cap'], row['Max_OT'], row['Prod_Weeks']
        p, o, s = 0, 0, 0
        
        if strat == "Chase (Prioritize OT)":
            p = base
            req = d - curr - p
            if req > 0:
                o = min(req, mx_ot)
                s = max(0, req - o)
                curr = 0
            else: curr = abs(req)

        elif strat == "Level Production":
            tgt = level_rate * w
            p = min(tgt, base)
            rem = tgt - p
            if rem > 0:
                o = min(rem, mx_ot)
                rem -= o
            if rem > 0: s = rem
            end = curr + p + o + s - d
            if end < 0: s += abs(end); curr = 0
            else: curr = end

        elif strat == "Subcontract Heavy":
            p = base
            req = d - curr - p
            if req > 0: s = req; curr = 0
            else: curr = abs(req)
        
        else: # Hybrid
            p = base
            req = d - curr - p
            if req > 0:
                o = min(req, mx_ot * 0.5)
                s = max(0, req - o)
                curr = 0
            else: curr = abs(req)

        prod.append(p); ot.append(o); sub.append(s); inv.append(curr)

    df['Std'] = prod; df['OT'] = ot; df['Sub'] = sub; df['Inv'] = inv[1:]
    # Cost Model
    df['Cost'] = (df['Std']*1.0) + (df['OT']*otr) + (df['Sub']*subr) + (df['Inv']*(hc/12))
    return df

res = run_model(d_mult, strategy, h_cost, ot_rate, sub_rate, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT
# -----------------------------------------------------------------------------
st.title("🔷 OATY 3.0 OPERATIONS DASHBOARD")

# --- BENCHMARKING ---
strats = ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"]
costs = {s: run_model(d_mult, s, h_cost, ot_rate, sub_rate, sunday)['Cost'].sum() for s in strats}
best_strat = min(costs, key=costs.get)
curr_cost = res['Cost'].sum()
diff = curr_cost - costs[best_strat]

# --- KPI CARDS ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("TOTAL COST", f"${curr_cost:,.0f}", delta=f"-${diff:,.0f} vs Optimal" if diff > 0 else "Best Choice", delta_color="inverse")
k2.metric("AVG INVENTORY", f"{res['Inv'].mean():,.0f}")
util = (res['Std'].sum() + res['OT'].sum()) / (res['Base_Cap'].sum() + res['Max_OT'].sum())
k3.metric("UTILIZATION", f"{util:.1%}")
k4.metric("OPTIMAL STRATEGY", best_strat.split(" ")[0].upper())

st.markdown("---")

# --- HIGH VISIBILITY CHARTS ---
c1, c2 = st.columns([2, 1])

# Common Axis Styling
axis_style = dict(
    showgrid=True, 
    gridcolor='#e5e7eb',
    tickfont=dict(size=12, color='black', family='Arial', weight='bold'),
    titlefont=dict(size=14, color='black', family='Arial', weight='bold')
)

with c1:
    st.markdown("#### PRODUCTION MIX vs DEMAND")
    fig = go.Figure()
    
    # 1. Standard (Blue)
    fig.add_trace(go.Bar(x=res['Month'], y=res['Std'], name='Standard', marker_color='#3b82f6'))
    # 2. Overtime (Dark Blue)
    fig.add_trace(go.Bar(x=res['Month'], y=res['OT'], name='Overtime', marker_color='#1e3a8a'))
    # 3. Subcontract (Orange for Contrast)
    fig.add_trace(go.Bar(x=res['Month'], y=res['Sub'], name='Subcontract', marker_color='#f97316'))
    # 4. Demand (Line)
    fig.add_trace(go.Scatter(x=res['Month'], y=res['Adj_Demand'], name='Demand', line=dict(color='#dc2626', width=4)))
    
    fig.update_layout(
        barmode='stack',
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='black', family='Arial'),
        legend=dict(orientation="h", y=1.1, font=dict(color="black")),
        height=450,
        xaxis=axis_style, yaxis=axis_style
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with c2:
    st.markdown("#### INVENTORY LEVELS")
    fig2 = go.Figure()
    
    fig2.add_trace(go.Scatter(
        x=res['Month'], y=res['Inv'], fill='tozeroy',
        mode='lines',
        line=dict(color='#10b981', width=3), # Green
        fillcolor='rgba(16, 185, 129, 0.2)',
        name='Inventory'
    ))
    
    fig2.add_hline(y=20000, line_dash="dash", line_color="#dc2626", annotation_text="Limit (20k)")
    
    fig2.update_layout(
        paper_bgcolor='white', plot_bgcolor='white',
        font=dict(color='black', family='Arial'),
        height=450,
        xaxis=axis_style, yaxis=dict(**axis_style, title="Units")
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- TABLE ---
st.markdown("---")
st.markdown("#### STRATEGY COMPARISON")

df_comp = pd.DataFrame([{"STRATEGY": k, "COST": v, "DIFF": v-costs[best_strat]} for k,v in costs.items()]).sort_values("COST")

# Use simple dataframe for maximum compatibility
st.dataframe(
    df_comp.style.format({"COST": "${:,.0f}", "DIFF": "+${:,.0f}"}),
    use_container_width=True, hide_index=True
)
