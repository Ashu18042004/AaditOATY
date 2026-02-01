# ==============================================================================
# OATY 3.0 OPERATIONS DASHBOARD - HIGH VISIBILITY & ROBUST CALCULATION
# ==============================================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. SETUP & ULTRA-HIGH CONTRAST STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Model", layout="wide")

st.markdown("""
    <style>
    /* 1. FORCE EVERYTHING TO BLACK AND WHITE */
    .stApp, .stMarkdown, .stDataFrame, .stTable {
        background-color: #ffffff !important;
        color: #000000 !important;
        font-family: 'Arial', sans-serif !important;
    }

    /* 2. HEADERS - BOLD AND BLACK */
    h1, h2, h3, h4, h5, h6, label {
        color: #000000 !important;
        font-weight: 900 !important; /* Maximum Boldness */
        text-transform: uppercase;
    }

    /* 3. METRIC CARDS - INK ON PAPER LOOK */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important;
        border: 3px solid #000000 !important; /* Thick Black Border */
        border-radius: 0px !important;
        padding: 10px !important;
        box-shadow: none !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #000000 !important;
        font-weight: bold !important;
        text-decoration: underline;
        font-size: 1.1rem !important;
    }
    div[data-testid="stMetricValue"] {
        color: #000000 !important;
        font-weight: 900 !important;
        font-size: 2.5rem !important;
    }

    /* 4. SIDEBAR - SEPARATION */
    section[data-testid="stSidebar"] {
        background-color: #ffffff !important;
        border-right: 3px solid #000000;
    }
    
    /* 5. DATAFRAMES - CLEAR GRIDS */
    div[data-testid="stDataFrame"] div[role="columnheader"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        font-weight: bold !important;
    }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE (CORRECTED CALCULATION LOGIC)
# -----------------------------------------------------------------------------
@st.cache_data
def get_clean_data():
    # Appendix 1.5 Data (Exact from Case)
    df = pd.DataFrame({
        "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
        "Prod_Weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        "Sales_Weeks": [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        "Demand": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000]
    })
    
    # Constants from Snippets
    CONSTANTS = {
        "Base_Cap_Wk": 16500.0,
        "OT_Limit_Wk": 7425.0,  # 18hrs is ~45% of 40hr week (16500 * 0.45 = 7425)
        "Sun_Limit_Wk": 3300.0, # 8hrs is ~20% of 40hr week (16500 * 0.20 = 3300)
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

strategy = st.sidebar.selectbox("STRATEGY", [
    "Chase (Prioritize OT)", 
    "Level Production", 
    "Subcontract Heavy", 
    "Hybrid"
])

st.sidebar.markdown("### 💰 COST PARAMETERS")
h_cost = st.sidebar.slider("HOLDING COST % (ANNUAL)", 10, 30, 20) / 100.0
ot_rate = st.sidebar.number_input("OT MULTIPLIER", 1.0, 2.5, 1.5)
sub_rate = st.sidebar.number_input("SUBCONTRACT MULTIPLIER", 1.0, 2.0, 1.25)
sunday = st.sidebar.checkbox("INCLUDE SUNDAY OT", value=False)

# -----------------------------------------------------------------------------
# 4. ROBUST CALCULATION ENGINE
# -----------------------------------------------------------------------------
def run_model(dm, strat, hc, otr, subr, sun):
    df = df_case.copy()
    
    # 1. Base Variables
    df['Adj_Demand'] = df['Demand'] * dm
    df['Base_Cap'] = df['Prod_Weeks'] * C['Base_Cap_Wk']
    
    ot_limit_factor = C['OT_Limit_Wk']
    if sun: ot_limit_factor += C['Sun_Limit_Wk']
    df['Max_OT'] = df['Prod_Weeks'] * ot_limit_factor
    
    # 2. Iterate for Continuity
    prod, ot, sub, inv = [], [], [], [0]
    curr_inv = 0
    
    # Level Target = Total Annual Demand / Total Prod Weeks
    total_ann_demand = df['Adj_Demand'].sum()
    total_prod_weeks = df['Prod_Weeks'].sum()
    level_weekly_rate = total_ann_demand / total_prod_weeks

    for i, row in df.iterrows():
        d = row['Adj_Demand']
        base_cap = row['Base_Cap']
        max_ot_cap = row['Max_OT']
        weeks = row['Prod_Weeks']
        
        p, o, s = 0, 0, 0
        
        # --- STRATEGY LOGIC ---
        if strat == "Chase (Prioritize OT)":
            # Produce strictly what is needed, up to capacity
            # Net requirement after inventory
            req = d - curr_inv
            
            if req <= 0:
                # Inventory covers it, produce 0 (or Min Base?)
                # Realistically, you pay Base cost regardless, so let's assume p=Base Cap is available
                # But "Chase" minimizes inventory.
                # However, usually Base Labor is Fixed. Let's produce Base Cap to avoid "Undertime" penalties not modeled here.
                # If we produce full base, we might build inventory.
                p = base_cap 
            else:
                # Need production
                if req <= base_cap:
                    p = base_cap # Fill base
                else:
                    p = base_cap
                    rem = req - base_cap
                    # Use OT
                    o = min(rem, max_ot_cap)
                    rem -= o
                    # Use Sub
                    if rem > 0:
                        s = rem
            
            # Update Inventory
            end_inv = curr_inv + p + o + s - d
            # Logic check: In Chase, we shouldn't have unintentional inventory unless Base Cap > Demand
            curr_inv = max(0, end_inv)

        elif strat == "Level Production":
            # Target constant weekly output
            target = level_weekly_rate * weeks
            
            # Fill Standard
            p = min(target, base_cap)
            rem = target - p
            
            # Fill OT
            if rem > 0:
                o = min(rem, max_ot_cap)
                rem -= o
            
            # Fill Sub (if Level plan requires it, which is rare, but possible if Target > Base+OT)
            if rem > 0:
                s = rem
            
            # Inventory Balance Check
            end_inv = curr_inv + p + o + s - d
            
            # If Stockout (Negative Inventory), Force Subcontract to fill gap
            if end_inv < 0:
                s += abs(end_inv)
                curr_inv = 0
            else:
                curr_inv = end_inv

        elif strat == "Subcontract Heavy":
            p = base_cap
            req = d - curr_inv - p
            if req > 0:
                s = req
                curr_inv = 0
            else:
                curr_inv = abs(req)
        
        else: # Hybrid (Balanced)
            p = base_cap
            req = d - curr_inv - p
            if req > 0:
                # Use 50% of Max OT
                o = min(req, max_ot_cap * 0.5)
                rem = req - o
                if rem > 0:
                    s = rem
                curr_inv = 0
            else:
                curr_inv = abs(req)

        prod.append(p); ot.append(o); sub.append(s); inv.append(curr_inv)

    df['Std_Units'] = prod
    df['OT_Units'] = ot
    df['Sub_Units'] = sub
    df['End_Inv'] = inv[1:]
    
    # 3. Financials (Full Cost Model)
    # Base Cost = $1/unit (Assumed standard)
    df['C_Base'] = df['Std_Units'] * 1.0 
    df['C_OT'] = df['OT_Units'] * otr     # e.g., $1.5
    df['C_Sub'] = df['Sub_Units'] * subr  # e.g., $1.25
    df['C_Hold'] = df['End_Inv'] * (hc / 12) # Monthly Holding
    
    df['Total_Cost'] = df['C_Base'] + df['C_OT'] + df['C_Sub'] + df['C_Hold']
    
    return df

res = run_model(d_mult, strategy, h_cost, ot_rate, sub_rate, sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT (BLACK & WHITE)
# -----------------------------------------------------------------------------
st.title("OATY 3.0: OPERATIONS ANALYTICS")
st.markdown(f"### SCENARIO: {scenario} | STRATEGY: {strategy}")

# --- KEY METRICS ---
total_cost = res['Total_Cost'].sum()
avg_inv = res['End_Inv'].mean()
peak_sub = res['Sub_Units'].max()
cap_util = (res['Std_Units'].sum() + res['OT_Units'].sum()) / (res['Base_Cap'].sum() + res['Max_OT'].sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("TOTAL COST", f"${total_cost:,.0f}")
k2.metric("AVG INVENTORY", f"{avg_inv:,.0f}")
k3.metric("UTILIZATION", f"{cap_util:.1%}")
k4.metric("PEAK SUBCONTRACT", f"{peak_sub:,.0f}")

st.markdown("---")

# --- CHARTS (HIGH CONTRAST) ---
c1, c2 = st.columns(2)

with c1:
    st.markdown("#### AGGREGATE PRODUCTION PLAN")
    fig = go.Figure()
    # Explicit Black/White colors
    fig.add_trace(go.Bar(x=res['Month'], y=res['Std_Units'], name='Standard', marker_color='#cccccc', marker_line_color='black', marker_line_width=1.5))
    fig.add_trace(go.Bar(x=res['Month'], y=res['OT_Units'], name='Overtime', marker_color='#666666', marker_line_color='black', marker_line_width=1.5))
    fig.add_trace(go.Bar(x=res['Month'], y=res['Sub_Units'], name='Subcontract', marker_color='#000000', marker_line_color='black', marker_line_width=1.5))
    # Demand Line
    fig.add_trace(go.Scatter(x=res['Month'], y=res['Adj_Demand'], name='Demand', line=dict(color='black', width=4, dash='dash')))
    
    fig.update_layout(
        barmode='stack', 
        template='plotly_white', 
        height=400,
        legend=dict(orientation="h", y=1.1, font=dict(color="black", size=12, family="Arial Black")),
        font=dict(color="black", family="Arial")
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("")

with c2:
    st.markdown("#### INVENTORY vs WAREHOUSE LIMIT")
    fig2 = px.area(res, x='Month', y='End_Inv')
    fig2.update_traces(line_color='black', fill_color='rgba(0,0,0,0.2)')
    fig2.add_hline(y=20000, line_dash="solid", line_color="black", annotation_text="Limit (20k)")
    fig2.update_layout(template='plotly_white', height=400, font=dict(color="black", family="Arial"))
    st.plotly_chart(fig2, use_container_width=True)

# --- COMPARISON TABLE ---
st.markdown("---")
st.markdown("### 🏆 STRATEGY BENCHMARKING (FULL COST MODEL)")

strats = ["Chase (Prioritize OT)", "Level Production", "Subcontract Heavy", "Hybrid"]
comp_rows = []

for s in strats:
    r = run_model(d_mult, s, h_cost, ot_rate, sub_rate, sunday)
    comp_rows.append({
        "STRATEGY": s,
        "TOTAL COST": r['Total_Cost'].sum(),
        "STD UNITS": r['Std_Units'].sum(),
        "OT UNITS": r['OT_Units'].sum(),
        "SUB UNITS": r['Sub_Units'].sum(),
        "HOLDING COST": r['C_Hold'].sum()
    })

df_comp = pd.DataFrame(comp_rows).sort_values("TOTAL COST")

st.dataframe(
    df_comp.style.format({
        "TOTAL COST": "${:,.0f}",
        "STD UNITS": "{:,.0f}",
        "OT UNITS": "{:,.0f}",
        "SUB UNITS": "{:,.0f}",
        "HOLDING COST": "${:,.0f}"
    }),
    use_container_width=True,
    hide_index=True
)

best_s = df_comp.iloc[0]['STRATEGY']
st.success(f"**OPTIMAL STRATEGY:** {best_s} minimizes Total Cost to **${df_comp.iloc[0]['TOTAL COST']:,.0f}**.")
