"""
OATY 3.0 Operations Planning Dashboard — Q3: How might production levels be changed
in the light of changes in the forecast demand?

Full operational planning analytics driven by OATY_Aadit.xlsx.
Run: streamlit run app.py
Dependencies: pip install streamlit pandas plotly openpyxl
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import numpy as np

# ---------------------------------------------------------------------------
# PAGE CONFIG — Premium blue theme, light background
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="OATY 3.0 Operations Planning",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for premium look, blue theme, light background, smooth feel
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .main { background: linear-gradient(180deg, #f0f4f8 0%, #e2e8f0 100%); }
    .stApp { background: #f8fafc; }
    h1, h2, h3 { color: #1e3a5f; font-weight: 700; }
    .kpi-card {
        background: linear-gradient(135deg, #ffffff 0%, #f1f5f9 100%);
        border: 1px solid #cbd5e1;
        border-radius: 12px;
        padding: 1.25rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
        margin-bottom: 1rem;
    }
    .kpi-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(30,58,95,0.08); }
    .kpi-title { color: #64748b; font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }
    .kpi-value { color: #1e3a5f; font-size: 1.75rem; font-weight: 700; }
    .insight-box {
        background: #ffffff;
        border-left: 4px solid #2563eb;
        border-radius: 8px;
        padding: 1rem 1.25rem;
        margin: 0.5rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    }
    div[data-testid="stMetricValue"] { font-weight: 700; color: #1e3a5f; }
    .stSlider label { font-weight: 500; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# DATA LOADING — All calculations from Excel (OATY_Aadit.xlsx)
# ---------------------------------------------------------------------------
@st.cache_data
def load_excel(excel_path: Path):
    """Load all required sheets from the case Excel file."""
    if not excel_path.exists():
        return None, f"File not found: {excel_path}. Place OATY_Aadit.xlsx in the app directory or run create_excel_from_case.py to generate it from the case exhibits."
    try:
        xl = pd.ExcelFile(excel_path)
        sheets = {}
        for name in ["Actual_1999", "Forecast_2000_weekly", "Volume_2000", "Costs"]:
            if name not in xl.sheet_names:
                return None, f"Required sheet '{name}' missing in Excel."
            sheets[name] = pd.read_excel(xl, sheet_name=name)
        if "Factory_loading_1999" in xl.sheet_names:
            sheets["Factory_loading_1999"] = pd.read_excel(xl, sheet_name="Factory_loading_1999")
        return sheets, None
    except Exception as e:
        return None, str(e)


def get_costs_dict(costs_df: pd.DataFrame):
    """Parse Costs sheet into a dict (Parameter -> Value)."""
    if costs_df is None or costs_df.empty:
        return {}
    # Handle column names (Parameter / Value or first two columns)
    cols = costs_df.columns.tolist()
    if "Parameter" in cols and "Value" in cols:
        return dict(zip(costs_df["Parameter"], costs_df["Value"]))
    return dict(zip(costs_df.iloc[:, 0], costs_df.iloc[:, 1]))


# ---------------------------------------------------------------------------
# STEP 1 — Monthly total demand, required production, capacity, surplus/shortage
# ---------------------------------------------------------------------------
def _col(df: pd.DataFrame, *candidates):
    """Return first existing column from candidates (handles spaces/underscores)."""
    for c in candidates:
        if c in df.columns:
            return df[c]
        alt = c.replace("_", " ")
        if alt in df.columns:
            return df[alt]
    raise KeyError(f"None of {candidates} in {list(df.columns)}")


def compute_step1(volume_df: pd.DataFrame, forecast_weekly: pd.DataFrame, capacity_per_week: float):
    """Compute required production, required standard hours, capacity utilization, surplus/shortage by month."""
    df = volume_df.copy()
    months = df["Month"].tolist()
    prod_weeks = _col(df, "Production_weeks").values
    total_demand = _col(df, "Total_months_demand").values
    capacity_per_month = capacity_per_week * prod_weeks
    required_production = total_demand
    # Standard hours: Consumer 80%, PC 100%, Professional 120% of PC (case). Weighted std-hr per drive from mix.
    if forecast_weekly is not None and not forecast_weekly.empty:
        tot = forecast_weekly["Total"].sum()
        c_share = forecast_weekly["Consumer"].sum() / tot if tot else 1/3
        p_share = forecast_weekly["PC"].sum() / tot if tot else 1/3
        r_share = forecast_weekly["Professional"].sum() / tot if tot else 1/3
        std_hr_per_drive = 0.8 * c_share + 1.0 * p_share + 1.2 * r_share
    else:
        std_hr_per_drive = 1.0
    required_std_hrs = total_demand * std_hr_per_drive
    utilization_pct = np.where(capacity_per_month > 0, (required_production / capacity_per_month) * 100, 0)
    surplus_shortage = capacity_per_month - required_production  # positive = surplus
    return pd.DataFrame({
        "Month": months,
        "Total_demand": total_demand,
        "Production_weeks": prod_weeks,
        "Capacity": capacity_per_month,
        "Required_production": required_production,
        "Required_std_hrs": required_std_hrs,
        "Utilization_pct": utilization_pct,
        "Surplus_shortage": surplus_shortage,
    })


# ---------------------------------------------------------------------------
# STEP 2 — Three demand scenarios: Base, +15%, -15%
# ---------------------------------------------------------------------------
def build_scenario_demands(volume_df: pd.DataFrame, scenario: str):
    """Return total_months_demand array for the chosen scenario (base / peak / slow)."""
    base = _col(volume_df, "Total_months_demand").values
    if scenario == "Base":
        return base.copy()
    if scenario == "Peak (+15%)":
        return base * 1.15
    if scenario == "Slow (-15%)":
        return base * 0.85
    return base.copy()


# ---------------------------------------------------------------------------
# STEP 3 — Required output, inventory, overtime, subcontract, cost per strategy
# ---------------------------------------------------------------------------
def run_level_production(demand_monthly: np.ndarray, capacity_monthly: np.ndarray,
                         prod_weeks: np.ndarray, holding_pct: float, overtime_rate: float = 1.5,
                         unit_cost: float = 100.0):
    """Level production: constant output rate; use overtime when level exceeds capacity; inventory absorbs fluctuation."""
    total_demand = demand_monthly.sum()
    total_capacity = capacity_monthly.sum()
    n = len(demand_monthly)
    # Level output = same share of total demand as share of capacity each month
    level_output = (total_demand / total_capacity) * capacity_monthly
    overtime_per_month = np.maximum(level_output - capacity_monthly, 0)
    overtime_units = float(overtime_per_month.sum())
    cum_prod = np.cumsum(level_output)
    cum_dem = np.cumsum(demand_monthly)
    inv = np.maximum(cum_prod - cum_dem, 0)
    holding_per_unit_month = unit_cost * (holding_pct / 100) / 12
    avg_inv = inv.mean() if n else 0
    cost_holding = avg_inv * holding_per_unit_month * 12
    cost_overtime = overtime_units * unit_cost * (overtime_rate - 1.0)
    return {
        "output": level_output,
        "inventory": inv,
        "overtime_units": overtime_units,
        "subcontract_units": 0.0,
        "cost_holding": cost_holding,
        "cost_overtime": cost_overtime,
        "cost_subcontract": 0.0,
        "total_cost": cost_holding + cost_overtime,
    }


def run_chase_overtime(demand_monthly: np.ndarray, capacity_monthly: np.ndarray,
                       overtime_rate: float, unit_cost: float = 100.0):
    """Chase demand with overtime when demand exceeds capacity."""
    n = len(demand_monthly)
    output = np.minimum(demand_monthly, capacity_monthly)
    shortage = np.maximum(demand_monthly - capacity_monthly, 0)
    overtime_units = shortage.sum()
    # Overtime cost: (overtime_rate - 1) * unit_cost per unit (premium over base)
    cost_overtime = overtime_units * unit_cost * (overtime_rate - 1.0)
    inv = np.zeros(n)
    holding_pct = 20.0
    cost_holding = 0.0
    return {
        "output": output + shortage,  # we meet demand with overtime
        "inventory": inv,
        "overtime_units": overtime_units,
        "subcontract_units": 0.0,
        "cost_holding": cost_holding,
        "cost_overtime": cost_overtime,
        "cost_subcontract": 0.0,
        "total_cost": cost_overtime,
    }


def run_hybrid(demand_monthly: np.ndarray, capacity_monthly: np.ndarray, prod_weeks: np.ndarray,
               holding_pct: float, overtime_rate: float, unit_cost: float = 100.0):
    """Hybrid: level production up to a cap, then overtime for the rest."""
    total_demand = demand_monthly.sum()
    total_capacity = capacity_monthly.sum()
    n = len(demand_monthly)
    level_output = (total_demand / total_capacity) * capacity_monthly
    level_output = np.minimum(level_output, capacity_monthly)
    shortage = np.maximum(demand_monthly - level_output, 0)
    overtime_units = shortage.sum()
    output = level_output + shortage
    cum_prod = np.cumsum(output)
    cum_dem = np.cumsum(demand_monthly)
    inv = np.maximum(cum_prod - cum_dem, 0)
    holding_per_unit_month = unit_cost * (holding_pct / 100) / 12
    avg_inv = inv.mean() if n else 0
    cost_holding = avg_inv * holding_per_unit_month * 12
    cost_overtime = overtime_units * unit_cost * (overtime_rate - 1.0)
    return {
        "output": output,
        "inventory": inv,
        "overtime_units": overtime_units,
        "subcontract_units": 0.0,
        "cost_holding": cost_holding,
        "cost_overtime": cost_overtime,
        "cost_subcontract": 0.0,
        "total_cost": cost_holding + cost_overtime,
    }


def run_subcontract_heavy(demand_monthly: np.ndarray, capacity_monthly: np.ndarray,
                          subcontract_pct: float, unit_cost: float = 100.0):
    """Subcontract when demand exceeds capacity."""
    shortage = np.maximum(demand_monthly - capacity_monthly, 0)
    subcontract_units = shortage.sum()
    cost_subcontract = subcontract_units * unit_cost * (subcontract_pct / 100 - 1.0)
    output = np.minimum(demand_monthly, capacity_monthly)
    inv = np.zeros(len(demand_monthly))
    return {
        "output": output,
        "inventory": inv,
        "overtime_units": 0.0,
        "subcontract_units": subcontract_units,
        "cost_holding": 0.0,
        "cost_overtime": 0.0,
        "cost_subcontract": cost_subcontract,
        "total_cost": cost_subcontract,
    }


# ---------------------------------------------------------------------------
# MAIN APP
# ---------------------------------------------------------------------------
def main():
    excel_path = Path(__file__).parent / "OATY_Aadit.xlsx"
    sheets, err = load_excel(excel_path)
    if err:
        st.error(err)
        st.info("Run `python3 create_excel_from_case.py` in this folder to generate OATY_Aadit.xlsx from the case exhibits.")
        return

    # Unpack sheets
    volume_df = sheets["Volume_2000"]
    forecast_weekly = sheets["Forecast_2000_weekly"]
    costs_df = sheets["Costs"]
    actual_1999 = sheets["Actual_1999"]

    costs = get_costs_dict(costs_df)
    capacity_per_week = float(costs.get("Capacity_drives_per_week", 16500))
    prod_weeks = _col(volume_df, "Production_weeks").values
    capacity_monthly = capacity_per_week * prod_weeks

    # STEP 1
    step1_df = compute_step1(volume_df, forecast_weekly, capacity_per_week)
    months = step1_df["Month"].tolist()

    # Sidebar — Section 3: Controls
    st.sidebar.header("Controls")
    scenario = st.sidebar.selectbox(
        "Demand scenario",
        ["Base", "Peak (+15%)", "Slow (-15%)"],
        index=0,
        help="Base = forecast; Peak = +15%; Slow = -15%",
    )
    strategy = st.sidebar.selectbox(
        "Strategy",
        ["Level production", "Chase (overtime)", "Hybrid", "Subcontract heavy"],
        index=0,
    )
    holding_pct = st.sidebar.slider("Holding cost (% annual)", 5, 40, 20, 1)
    overtime_rate = st.sidebar.slider("Overtime rate (multiplier)", 1.2, 2.0, 1.5, 0.05)
    subcontract_pct = st.sidebar.slider("Subcontract cost (% of factory)", 115, 130, 122, 1)

    # Demand for selected scenario
    demand_monthly = build_scenario_demands(volume_df, scenario)

    # STEP 3 for selected scenario and strategy
    unit_cost = 100.0  # base for relative cost
    if strategy == "Level production":
        res = run_level_production(demand_monthly, capacity_monthly, prod_weeks, holding_pct, overtime_rate, unit_cost)
    elif strategy == "Chase (overtime)":
        res = run_chase_overtime(demand_monthly, capacity_monthly, overtime_rate, unit_cost)
    elif strategy == "Hybrid":
        res = run_hybrid(demand_monthly, capacity_monthly, prod_weeks, holding_pct, overtime_rate, unit_cost)
    else:
        res = run_subcontract_heavy(demand_monthly, capacity_monthly, subcontract_pct, unit_cost)

    # STEP 4 — Compare all strategies for current scenario (for chart and recommendation)
    scenario_demand = build_scenario_demands(volume_df, scenario)
    strategies_run = {}
    for s in ["Level production", "Chase (overtime)", "Hybrid", "Subcontract heavy"]:
        if s == "Level production":
            strategies_run[s] = run_level_production(scenario_demand, capacity_monthly, prod_weeks, holding_pct, overtime_rate, unit_cost)
        elif s == "Chase (overtime)":
            strategies_run[s] = run_chase_overtime(scenario_demand, capacity_monthly, overtime_rate, unit_cost)
        elif s == "Hybrid":
            strategies_run[s] = run_hybrid(scenario_demand, capacity_monthly, prod_weeks, holding_pct, overtime_rate, unit_cost)
        else:
            strategies_run[s] = run_subcontract_heavy(scenario_demand, capacity_monthly, subcontract_pct, unit_cost)
    best_strategy = min(strategies_run.keys(), key=lambda x: strategies_run[x]["total_cost"])

    # ---------- Section 1: KPI Cards ----------
    st.title("OATY 3.0 — Operations Planning Dashboard")
    st.caption("Q3: How might production levels be changed in the light of changes in forecast demand? | Data: OATY_Aadit.xlsx")

    total_demand = float(np.sum(demand_monthly))
    avg_util = float(step1_df["Utilization_pct"].mean())
    total_shortage = float(np.sum(np.maximum(-step1_df["Surplus_shortage"].values, 0)))
    total_surplus = float(np.sum(np.maximum(step1_df["Surplus_shortage"].values, 0)))
    est_cost = res["total_cost"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total demand (drives)", f"{total_demand:,.0f}", help="Sum of monthly demand for selected scenario")
    with col2:
        st.metric("Avg capacity utilization (%)", f"{avg_util:.1f}%", help="Average of monthly utilization")
    with col3:
        st.metric("Shortage / Excess (drives)", f"{total_shortage:,.0f} / {total_surplus:,.0f}", help="Total shortage vs excess vs capacity")
    with col4:
        st.metric("Estimated cost (relative)", f"{est_cost:,.0f}", help="Total cost for selected strategy (base unit cost = 100)")

    # ---------- Section 2: Graphs ----------
    st.header("Section 2: Graphs")

    # Monthly demand vs capacity
    fig_demand_cap = go.Figure()
    fig_demand_cap.add_trace(go.Scatter(x=months, y=demand_monthly, name="Demand", line=dict(color="#2563eb", width=2), mode="lines+markers"))
    fig_demand_cap.add_trace(go.Scatter(x=months, y=capacity_monthly, name="Capacity", line=dict(color="#64748b", width=2, dash="dash"), mode="lines+markers"))
    fig_demand_cap.update_layout(
        title="Monthly demand vs capacity",
        xaxis_title="Month",
        yaxis_title="Drives",
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
        margin=dict(t=60),
        font=dict(size=12),
        plot_bgcolor="rgba(248,250,252,1)",
        paper_bgcolor="rgba(255,255,255,0.9)",
    )
    st.plotly_chart(fig_demand_cap, use_container_width=True)

    # Stacked product mix (from forecast 2000)
    mix_df = forecast_weekly.set_index("Month")[["Consumer", "PC", "Professional"]]
    fig_mix = px.area(
        mix_df.reset_index(), x="Month", y=["Consumer", "PC", "Professional"],
        title="Stacked product mix (Forecast 2000 weekly avg)",
        color_discrete_sequence=["#3b82f6", "#1d4ed8", "#1e40af"],
    )
    fig_mix.update_layout(template="plotly_white", hovermode="x unified", margin=dict(t=60), yaxis_title="Drives/week")
    st.plotly_chart(fig_mix, use_container_width=True)

    # Inventory levels (from selected strategy)
    fig_inv = go.Figure()
    fig_inv.add_trace(go.Bar(x=months, y=res["inventory"], name="Inventory", marker_color="#2563eb"))
    fig_inv.update_layout(
        title=f"Inventory levels — {strategy}",
        xaxis_title="Month",
        yaxis_title="Drives",
        template="plotly_white",
        margin=dict(t=60),
    )
    st.plotly_chart(fig_inv, use_container_width=True)

    # Overtime hours / units (across strategies for comparison)
    strat_names = list(strategies_run.keys())
    overtime_vals = [strategies_run[s]["overtime_units"] for s in strat_names]
    fig_ot = go.Figure(data=[go.Bar(x=strat_names, y=overtime_vals, marker_color="#1e40af")])
    fig_ot.update_layout(
        title="Overtime units by strategy (current scenario)",
        xaxis_title="Strategy",
        yaxis_title="Overtime (drive-equivalent)",
        template="plotly_white",
        margin=dict(t=60),
    )
    st.plotly_chart(fig_ot, use_container_width=True)

    # Strategy cost comparison
    cost_vals = [strategies_run[s]["total_cost"] for s in strat_names]
    fig_cost = go.Figure(data=[go.Bar(x=strat_names, y=cost_vals, marker_color="#2563eb")])
    fig_cost.update_layout(
        title="Strategy cost comparison (relative cost)",
        xaxis_title="Strategy",
        yaxis_title="Total cost",
        template="plotly_white",
        margin=dict(t=60),
    )
    st.plotly_chart(fig_cost, use_container_width=True)

    # Scenario comparison: total demand by scenario
    scenarios = ["Base", "Peak (+15%)", "Slow (-15%)"]
    scenario_totals = [np.sum(build_scenario_demands(volume_df, s)) for s in scenarios]
    fig_scenario = go.Figure(data=[go.Bar(x=scenarios, y=scenario_totals, marker_color=["#3b82f6", "#1d4ed8", "#60a5fa"])])
    fig_scenario.update_layout(
        title="Total annual demand by scenario",
        xaxis_title="Scenario",
        yaxis_title="Total demand (drives)",
        template="plotly_white",
        margin=dict(t=60),
    )
    st.plotly_chart(fig_scenario, use_container_width=True)

    # ---------- Section 4: Insights ----------
    st.header("Section 4: Insights")
    bottleneck_months = step1_df[step1_df["Utilization_pct"] > 100]["Month"].tolist()
    if not bottleneck_months:
        bottleneck_months = step1_df.nlargest(3, "Utilization_pct")["Month"].tolist()
    overtime_months = step1_df[step1_df["Surplus_shortage"] < 0]["Month"].tolist()

    insight1 = f"**Bottleneck months (highest utilization):** {', '.join(bottleneck_months)}. Focus capacity or overtime here."
    insight2 = f"**Overtime needed in months:** {', '.join(overtime_months) if overtime_months else 'None in base capacity.'}"
    insight3 = f"**Best strategy (lowest cost, current parameters):** **{best_strategy}** — recommended for this scenario and cost assumptions."

    st.markdown(f'<div class="insight-box">{insight1}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="insight-box">{insight2}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="insight-box">{insight3}</div>', unsafe_allow_html=True)

    # Optional: Step 1 detail table (monthly required production, std hours, utilization)
    with st.expander("Step 1 — Monthly detail (required production, standard hours, utilization)"):
        display_df = step1_df[["Month", "Total_demand", "Required_production", "Required_std_hrs", "Capacity", "Utilization_pct", "Surplus_shortage"]].copy()
        display_df["Required_std_hrs"] = display_df["Required_std_hrs"].round(0)
        st.dataframe(display_df, use_container_width=True)

    st.sidebar.markdown("---")
    st.sidebar.caption("OATY 3.0 | Data: OATY_Aadit.xlsx | All calculations from Excel.")


if __name__ == "__main__":
    main()
