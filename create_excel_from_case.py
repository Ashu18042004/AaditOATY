"""
Creates OATY_Aadit.xlsx from OATY 3.0 case exhibits (Appendix 1.1, 1.2, 1.3, 1.4, 1.5).
Run once if the Excel file does not exist. The dashboard reads from OATY_Aadit.xlsx.
"""
import pandas as pd
from pathlib import Path

OUTPUT = Path(__file__).parent / "OATY_Aadit.xlsx"

# Appendix 1.1 - Actual 1999 orders (weekly avg in unit drives)
actual_1999 = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Consumer": [5500, 5190, 5950, 7100, 5500, 5050, 4900, 4750, 5050, 5600, 5150, 7550],
    "PC": [7950, 7560, 8800, 10400, 8300, 7250, 7190, 7050, 7550, 7750, 8800, 12150],
    "Professional": [2750, 2650, 3050, 3500, 2700, 2500, 2410, 2350, 2550, 2700, 2600, 3800],
    "Total": [16200, 15400, 17800, 21000, 16500, 14800, 14500, 14150, 15150, 16050, 16550, 23500],
})

# Appendix 1.3 - 2000 forecast (weekly avg in unit drives)
forecast_2000_weekly = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Consumer": [5960, 6090, 6030, 6540, 5800, 5000, 5000, 5000, 5000, 5500, 5600, 8000],
    "PC": [8940, 9550, 9510, 9770, 8450, 7500, 7500, 7500, 8000, 8200, 8500, 12000],
    "Professional": [2980, 3220, 3160, 3290, 2900, 2500, 2500, 2500, 2500, 2800, 2900, 4000],
    "Total": [17800, 18860, 18700, 19600, 17150, 15000, 15000, 15000, 15500, 16500, 17000, 24000],
})

# Appendix 1.5 - 2000 volume planning (unit drives)
volume_2000 = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Production_weeks": [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
    "Sales_weeks": [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
    "Avg_weekly_demand": [17880, 18860, 18700, 19600, 17150, 15000, 15000, 15000, 15500, 16500, 17000, 24000],
    "Total_months_demand": [71520, 75440, 93500, 78400, 85750, 60000, 60000, 75000, 62000, 82500, 68000, 96000],
    "Cumulative_demand": [71520, 146960, 240460, 318860, 404610, 464610, 524610, 599610, 661610, 744110, 812110, 908110],
})

# Appendix 1.4 - Cost assumptions
costs = pd.DataFrame({
    "Parameter": [
        "Holding_cost_pct_annual", "Overtime_weekday_mult", "Overtime_sunday_mult",
        "Subcontract_cost_min_pct", "Subcontract_cost_max_pct",
        "Capacity_drives_per_week", "Warehouse_capacity_drives"
    ],
    "Value": [20, 1.5, 2.0, 120, 125, 16500, 20000],
})

# Appendix 1.2 - Factory loading (standard hours/week) - last column is actual
factory_loading = pd.DataFrame({
    "Month": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "Forecast_Jan": [14500, 15050, 15900, 20500, 17050, 14300, 15000, 13100, 14200, 14800, 16300, 18700],
    "Actual_std_hrs": [14850, 14500, 16150, 19200, 15400, 13600, 13300, 13000, 13900, 14700, 15150, 21500],
})

with pd.ExcelWriter(OUTPUT, engine="openpyxl") as writer:
    actual_1999.to_excel(writer, sheet_name="Actual_1999", index=False)
    forecast_2000_weekly.to_excel(writer, sheet_name="Forecast_2000_weekly", index=False)
    volume_2000.to_excel(writer, sheet_name="Volume_2000", index=False)
    costs.to_excel(writer, sheet_name="Costs", index=False)
    factory_loading.to_excel(writer, sheet_name="Factory_loading_1999", index=False)

print(f"Created {OUTPUT}")
