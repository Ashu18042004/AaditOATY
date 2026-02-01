# ==============================================================================
# OATY 3.0 OPERATIONS DASHBOARD - HIGH CONTRAST & VISIBILITY FIXED
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. VISUAL SETUP (STRICT WHITE BACKGROUND ENFORCEMENT)
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 High Vis", layout="wide")

st.markdown("""
    <style>
    /* 1. Force Main App Background to White */
    .stApp {
        background-color: #ffffff !important;
        color: #000000 !important;
    }
    
    /* 2. Metric Cards (Black Borders, High Contrast) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 2px solid #000000 !important;
        color: #000000 !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: bold !important;
        text-decoration: underline;
    }
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 900 !important;
    }

    /* 3. Headers */
    h1, h2, h3 {
        color: #000000 !important;
        text-transform: uppercase;
        font-weight: 800;
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
        "OT_Limit_Wk": 7425.0,  # 45% of Base
        "Sun_Limit_Wk": 3300.0, # 20% of Base
        "Whse_Cap": 20000.0
    }
    return df, CONSTANTS

df_case, C = get_data()

# -----------------------------------------------------------------------------
# 3. CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.markdown("### 🛠 MODEL CONTROLS")
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
# 5. DASHBOARD LAYOUT (FIXED VISIBILITY)
# -----------------------------------------------------------------------------
st.title("OATY 3.0 OPERATIONS DASHBOARD")

# --- BENCHMARKING (THINKING ENGINE) ---
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

with c1:
    st.markdown("#### PRODUCTION vs DEMAND (Stack)")
    fig = go.Figure()
    
    # 1. Standard (Light Grey - Distinct)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['Std'], name='Standard',
        marker_color='#D3D3D3', marker_line_color='black', marker_line_width=1.5
    ))
    # 2. Overtime (Dark Grey)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['OT'], name='Overtime',
        marker_color='#696969', marker_line_color='black', marker_line_width=1.5
    ))
    # 3. Subcontract (Pure Black)
    fig.add_trace(go.Bar(
        x=res['Month'], y=res['Sub'], name='Subcontract',
        marker_color='#000000', marker_line_color='white', marker_line_width=1
    ))
    # 4. Demand Line (Red for high visibility)
    fig.add_trace(go.Scatter(
        x=res['Month'], y=res['Adj_Demand'], name='Demand',
        line=dict(color='#FF0000', width=4, dash='solid')
    ))
    
    # FORCE WHITE BACKGROUND
    fig.update_layout(
        barmode='stack',
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='black', size=14, family='Arial'),
        legend=dict(orientation="h", y=1.1),
        height=450,
        yaxis=dict(showgrid=True, gridcolor='#E5E5E5')
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with c2:
    st.markdown("#### INVENTORY LEVELS (Visible Area)")
    fig2 = go.Figure()
    
    # Area Chart with VISIBLE fill
    fig2.add_trace(go.Scatter(
        x=res['Month'], y=res['Inv'], fill='tozeroy',
        mode='lines',
        line=dict(color='black', width=3),
        fillcolor='rgba(100, 100, 100, 0.4)', # Darker fill for visibility
        name='Inventory'
    ))
    
    # Limit Line
    fig2.add_hline(y=20000, line_dash="dash", line_color="red", annotation_text="Limit (20k)")
    
    # FORCE WHITE BACKGROUND
    fig2.update_layout(
        paper_bgcolor='white',
        plot_bgcolor='white',
        font=dict(color='black', size=14, family='Arial'),
        height=450,
        yaxis=dict(showgrid=True, gridcolor='#E5E5E5', title="Units"),
        xaxis=dict(showgrid=False)
    )
    st.plotly_chart(fig2, use_container_width=True)

# --- STRATEGY TABLE ---
st.markdown("---")
st.markdown("#### COST COMPARISON")
df_comp = pd.DataFrame([{"STRATEGY": k, "COST": v} for k,v in costs.items()]).sort_values("COST")
st.dataframe(
    df_comp.style.format({"COST": "${:,.0f}"}),
    use_container_width=True, 
    hide_index=True
)
