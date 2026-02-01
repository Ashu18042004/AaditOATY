import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(page_title="OATY 3.0 Ops Strategy", layout="wide", page_icon="🏭")

# Custom CSS for Professional Blue/White Theme
st.markdown("""
    <style>
    /* Main Background */
    .stApp { background-color: #F4F6F9; }
    
    /* Headings */
    h1, h2, h3 { color: #0f2557; font-family: 'Helvetica Neue', sans-serif; font-weight: 700; }
    
    /* Metrics Cards */
    div[data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #2e86de;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Tables */
    .dataframe { font-size: 14px; }
    
    /* Sidebar */
    section[data-testid="stSidebar"] { background-color: #0f2557; }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] label { color: #ffffff; }
    </style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA ENGINE
# -----------------------------------------------------------------------------
@st.cache_data
def get_data():
    try:
        # Load the generated Excel file
        xls = pd.ExcelFile('OATY_Aadit.xlsx')
        df_vol = pd.read_excel(xls, 'Volume_Planning')
        df_seg = pd.read_excel(xls, 'Segment_Mix')
        df_inp = pd.read_excel(xls, 'Inputs')
        
        # Extract constants for easy access
        const = dict(zip(df_inp['Parameter'], df_inp['Value']))
        return df_vol, df_seg, const
    except FileNotFoundError:
        st.error("Data file 'OATY_Aadit.xlsx' not found. Please run the data generator script first.")
        st.stop()

df_vol, df_seg, CONSTANTS = get_data()

# -----------------------------------------------------------------------------
# 3. SIDEBAR CONTROLS
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ Operations Control")
st.sidebar.markdown("---")

# Scenario Selection
scenario = st.sidebar.selectbox("Demand Scenario", ["Base Forecast (Case)", "Growth (+15%)", "Recession (-15%)"])
demand_mult = 1.15 if "Growth" in scenario else (0.85 if "Recession" in scenario else 1.0)

# Strategy Selection
strategy_mode = st.sidebar.selectbox("Planning Strategy", [
    "Chase Demand (Use Overtime)", 
    "Level Production (Build Inventory)", 
    "Subcontract Heavy (Min Assets)", 
    "Hybrid (Balanced)"
])

st.sidebar.markdown("### Cost Drivers")
holding_rate = st.sidebar.slider("Annual Holding Cost %", 10, 40, int(CONSTANTS['Holding Cost (Annual %)']*100)) / 100.0
ot_mult = st.sidebar.number_input("Overtime Multiplier", 1.0, 3.0, CONSTANTS['OT Cost Multiplier (Weekday)'], 0.1)
sub_mult = st.sidebar.number_input("Subcontract Multiplier", 1.0, 2.0, CONSTANTS['Subcontract Cost Multiplier'], 0.05)
allow_sunday = st.sidebar.checkbox("Allow Sunday Work?", value=False)

# -----------------------------------------------------------------------------
# 4. CALCULATION ENGINE (THE BRAIN)
# -----------------------------------------------------------------------------
def run_simulation(d_mult, strat, h_cost, ot_cost_m, sub_cost_m, sunday_allowed):
    # Setup working dataframe
    df = df_vol.copy()
    
    # Apply Demand Multiplier
    df['Demand'] = df['Total_Demand'] * d_mult
    
    # Calculate Capacities (Weeks * Weekly Capacity)
    df['Cap_Regular'] = df['Production_Weeks'] * CONSTANTS['Weekly Base Capacity']
    
    # OT Capacity: (Weekday/Sat Limit * Weeks) + (Sunday Limit * Weeks if allowed)
    ot_per_week = CONSTANTS['Weekday+Sat OT Limit (Units/Wk)']
    if sunday_allowed:
        ot_per_week += CONSTANTS['Sunday OT Limit (Units/Wk)']
        
    df['Cap_Max_OT'] = df['Production_Weeks'] * ot_per_week
    
    # Initialize Tracking Lists
    prod_std, prod_ot, prod_sub, closing_inv = [], [], [], []
    current_inv = 0 # Starting Inventory assumed 0 per case
    
    # Calculate Level Target (Total Demand / Total Weeks)
    total_annual_demand = df['Demand'].sum()
    total_weeks = df['Production_Weeks'].sum()
    level_weekly_rate = total_annual_demand / total_weeks
    
    for i, row in df.iterrows():
        demand = row['Demand']
        reg_cap = row['Cap_Regular']
        ot_cap = row['Cap_Max_OT']
        weeks = row['Production_Weeks']
        
        # Decision Variables
        p_std = 0
        p_ot = 0
        p_sub = 0
        
        # Strategy Logic
        if strat == "Chase Demand (Use Overtime)":
            # Produce standard max
            p_std = reg_cap
            # Check gap
            gap = demand - p_std - current_inv
            if gap > 0:
                p_ot = min(gap, ot_cap) # Use OT up to limit
                p_sub = max(0, gap - p_ot) # Subcontract rest
            
        elif strat == "Level Production (Build Inventory)":
            # Target constant weekly output
            target = level_weekly_rate * weeks
            
            # Fill standard first
            p_std = min(target, reg_cap)
            remainder = target - p_std
            
            # Use OT if target > regular capacity
            if remainder > 0:
                p_ot = min(remainder, ot_cap)
                p_sub = max(0, remainder - p_ot)
            
            # Inventory adjustment (Force Subcontract if Inventory goes negative)
            projected_inv = current_inv + p_std + p_ot + p_sub - demand
            if projected_inv < 0:
                p_sub += abs(projected_inv) # Emergency Subcontract
            
        elif strat == "Subcontract Heavy (Min Assets)":
            # Only use regular capacity, then subcontract everything
            p_std = reg_cap
            gap = demand - p_std - current_inv
            if gap > 0:
                p_sub = gap
                
        elif strat == "Hybrid (Balanced)":
            # Use 50% of available OT, then Subcontract
            p_std = reg_cap
            gap = demand - p_std - current_inv
            if gap > 0:
                p_ot = min(gap, ot_cap * 0.5)
                p_sub = max(0, gap - p_ot)

        # Update Inventory
        total_prod = p_std + p_ot + p_sub
        end_inv = current_inv + total_prod - demand
        
        # Store Results
        prod_std.append(p_std)
        prod_ot.append(p_ot)
        prod_sub.append(p_sub)
        closing_inv.append(end_inv)
        current_inv = max(0, end_inv) # Carry forward

    # Assign to DataFrame
    df['Prod_Std'] = prod_std
    df['Prod_OT'] = prod_ot
    df['Prod_Sub'] = prod_sub
    df['Inventory'] = closing_inv
    
    # Financials (Base Cost = 1 Unit)
    df['Cost_Base'] = df['Prod_Std'] * 1.0
    df['Cost_OT'] = df['Prod_OT'] * ot_cost_m
    df['Cost_Sub'] = df['Prod_Sub'] * sub_cost_m
    df['Cost_Hold'] = df['Inventory'] * (h_cost / 12) # Monthly Holding Cost
    
    df['Total_Cost'] = df['Cost_Base'] + df['Cost_OT'] + df['Cost_Sub'] + df['Cost_Hold']
    
    return df

# Run Active Simulation
results = run_simulation(demand_mult, strategy_mode, holding_rate, ot_mult, sub_mult, allow_sunday)

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT
# -----------------------------------------------------------------------------

st.title("🏭 OATY 3.0: Operational Planning Dashboard")
st.markdown(f"**Scenario:** {scenario} | **Strategy:** {strategy_mode}")

# --- Section 1: KPI Cards ---
col1, col2, col3, col4 = st.columns(4)

total_cost = results['Total_Cost'].sum()
avg_inv = results['Inventory'].mean()
max_shortfall = results['Prod_Sub'].sum() # Proxy for shortfall covered by external
utilization = (results['Prod_Std'].sum() + results['Prod_OT'].sum()) / (results['Cap_Regular'].sum() + results['Cap_Max_OT'].sum())

col1.metric("Total Operational Cost", f"${total_cost:,.0f}", delta_color="inverse")
col2.metric("Avg Inventory Level", f"{avg_inv:,.0f} units")
col3.metric("Capacity Utilization", f"{utilization:.1%}")
col4.metric("Outsourced Units", f"{max_shortfall:,.0f}", help="Units produced via Subcontracting")

st.markdown("---")

# --- Section 2: Main Charts ---
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("Monthly Demand vs. Capacity Stack")
    fig_cap = go.Figure()
    
    # Stacked Bars for Production
    fig_cap.add_trace(go.Bar(x=results['Month'], y=results['Prod_Std'], name='Regular Production', marker_color='#2e86de'))
    fig_cap.add_trace(go.Bar(x=results['Month'], y=results['Prod_OT'], name='Overtime', marker_color='#ee5253'))
    fig_cap.add_trace(go.Bar(x=results['Month'], y=results['Prod_Sub'], name='Subcontract', marker_color='#f39c12'))
    
    # Line for Demand
    fig_cap.add_trace(go.Scatter(x=results['Month'], y=results['Demand'], name='Total Demand', 
                                 line=dict(color='#0f2557', width=4, dash='solid')))
    
    fig_cap.update_layout(barmode='stack', height=400, template='plotly_white', legend=dict(orientation="h", y=1.1))
    st.plotly_chart(fig_cap, use_container_width=True)

with c2:
    st.subheader("Inventory vs. Warehouse Cap")
    fig_inv = go.Figure()
    fig_inv.add_trace(go.Scatter(x=results['Month'], y=results['Inventory'], fill='tozeroy', 
                                 name='Inventory', line_color='#1dd1a1'))
    
    # Warehouse Limit Line
    fig_inv.add_hline(y=CONSTANTS['Warehouse Capacity'], line_dash="dash", line_color="red", 
                      annotation_text="Limit (20k)")
    
    fig_inv.update_layout(height=400, template='plotly_white')
    st.plotly_chart(fig_inv, use_container_width=True)

# --- Section 3: Deep Dive & Comparisons ---
c3, c4 = st.columns(2)

with c3:
    st.subheader("Cost Structure Breakdown")
    cost_data = results[['Cost_Base', 'Cost_OT', 'Cost_Sub', 'Cost_Hold']].sum().reset_index()
    cost_data.columns = ['Type', 'Value']
    fig_pie = px.pie(cost_data, values='Value', names='Type', hole=0.4, 
                     color_discrete_sequence=['#2e86de', '#ee5253', '#f39c12', '#1dd1a1'])
    st.plotly_chart(fig_pie, use_container_width=True)

with c4:
    st.subheader("Strategy Comparison (Benchmarking)")
    
    # Run all strategies in background
    strategies = ["Chase Demand (Use Overtime)", "Level Production (Build Inventory)", "Subcontract Heavy (Min Assets)", "Hybrid (Balanced)"]
    comp_data = []
    
    for s in strategies:
        res = run_simulation(demand_mult, s, holding_rate, ot_mult, sub_mult, allow_sunday)
        comp_data.append({
            "Strategy": s,
            "Total Cost": res['Total_Cost'].sum(),
            "Max Inventory": res['Inventory'].max(),
            "Subcontracted": res['Prod_Sub'].sum()
        })
    
    df_comp = pd.DataFrame(comp_data)
    df_comp = df_comp.sort_values("Total Cost")
    
    st.dataframe(
        df_comp.style.format({"Total Cost": "${:,.0f}", "Max Inventory": "{:,.0f}", "Subcontracted": "{:,.0f}"})
        .background_gradient(subset=['Total Cost'], cmap='Blues_r'),
        use_container_width=True
    )

# --- Section 4: Automated Insights ---
st.markdown("---")
st.subheader("💡 Operational Insights")

best_strat = df_comp.iloc[0]['Strategy']
lowest_cost = df_comp.iloc[0]['Total Cost']

bottlenecks = results[results['Prod_Sub'] > 0]['Month'].tolist()
wh_breach = results[results['Inventory'] > CONSTANTS['Warehouse Capacity']]['Month'].tolist()

col_i1, col_i2 = st.columns(2)

with col_i1:
    st.info(f"**Recommendation:** The most cost-effective strategy is **{best_strat}** at **${lowest_cost:,.0f}**.")
    if wh_breach:
        st.warning(f"**Warehouse Warning:** Inventory exceeds 20k limit in: {', '.join(wh_breach)}. Consider renting external space.")
    else:
        st.success("Warehouse capacity is respected throughout the year.")

with col_i2:
    if bottlenecks:
        st.error(f"**Capacity Bottlenecks:** Demand exceeds internal capacity (Regular + OT) in **{', '.join(bottlenecks)}**. External subcontractors are required.")
    else:
        st.success("Internal capacity is sufficient to meet demand without subcontracting.")

# Footer
st.markdown("---")
st.caption("OATY 3.0 Dashboard | Operations Management | Developed with Streamlit")
