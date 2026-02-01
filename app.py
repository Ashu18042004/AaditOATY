"""
Mandexor Memory Production Planning Dashboard
OATY 3.0 Case Study - Question 3 Analysis

Simplified version with robust error handling
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Mandexor Memory - Production Planning Dashboard",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

# Simple CSS without gradient issues
st.markdown("""
    <style>
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
        color: #1f77b4;
    }
    .medium-font {
        font-size: 18px !important;
        font-weight: bold;
        color: #2ca02c;
    }
    </style>
""", unsafe_allow_html=True)

# Load data
@st.cache_data
def load_case_data():
    """Load all case study data"""
    
    # Demand data from case (Appendix 1.3 and 1.5)
    demand_data = pd.DataFrame({
        'Month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
        'Production_weeks': [4, 3, 4, 4, 5, 4, 3, 3, 4, 5, 4, 4],
        'Sales_weeks': [4, 4, 5, 4, 5, 4, 4, 5, 4, 5, 4, 4],
        'Avg_weekly_demand': [17880, 18860, 18700, 19600, 17150, 15000,
                             15000, 15000, 15500, 16500, 17000, 24000],
        'Total_monthly_demand': [71520, 75440, 93500, 78400, 85750, 60000,
                                60000, 75000, 62000, 82500, 68000, 96000]
    })
    
    params = {
        'weekly_capacity': 16500,
        'inventory_holding_cost': 0.20,
        'overtime_cost_weekday': 1.50,
        'overtime_cost_sunday': 2.00,
        'subcontract_cost': 1.25,
        'warehouse_capacity': 20000,
        'opening_inventory': 0
    }
    
    return demand_data, params

class ProductionPlanner:
    """Production planning with scenario analysis"""
    
    def __init__(self, demand_data, params):
        self.demand_data = demand_data.copy()
        self.params = params
        
    def apply_scenario(self, scenario='base'):
        """Apply demand scenario"""
        df = self.demand_data.copy()
        
        if scenario == 'optimistic':
            df['Total_monthly_demand'] *= 1.15
            df['Avg_weekly_demand'] *= 1.15
        elif scenario == 'pessimistic':
            df['Total_monthly_demand'] *= 0.85
            df['Avg_weekly_demand'] *= 0.85
        elif scenario == 'volatile':
            np.random.seed(42)
            variation = np.random.uniform(0.8, 1.2, len(df))
            df['Total_monthly_demand'] *= variation
            df['Avg_weekly_demand'] *= variation
        
        # Calculate capacity
        df['Normal_capacity'] = df['Production_weeks'] * self.params['weekly_capacity']
        df['Capacity_gap'] = df['Total_monthly_demand'] - df['Normal_capacity']
        
        return df
    
    def optimize_strategy(self, demand_df, ot_weight=0.6, sub_weight=0.4):
        """Optimize production strategy"""
        results = []
        inventory = self.params['opening_inventory']
        total_cost = 0
        
        for idx, row in demand_df.iterrows():
            demand = row['Total_monthly_demand']
            capacity = row['Normal_capacity']
            gap = row['Capacity_gap']
            
            overtime = 0
            subcontract = 0
            cost = 0
            
            if gap <= 0:  # Excess capacity
                inventory += abs(gap)
                cost = inventory * 0.02  # Monthly holding cost
                strategy = 'Inventory Build'
            else:  # Shortfall
                # Use inventory first
                from_inventory = min(gap, inventory)
                inventory -= from_inventory
                remaining = gap - from_inventory
                
                if remaining > 0:
                    # Allocate between overtime and subcontract
                    max_overtime = capacity * 0.1  # 10% via overtime
                    overtime = min(remaining * ot_weight, max_overtime)
                    subcontract = remaining - overtime
                    
                    cost = (overtime * 150) + (subcontract * 125)  # Simplified cost
                
                strategy = 'Mixed' if subcontract > 0 else 'Overtime'
            
            total_cost += cost
            
            results.append({
                'Month': row['Month'],
                'Demand': demand,
                'Capacity': capacity,
                'Gap': gap,
                'Overtime': overtime,
                'Subcontract': subcontract,
                'Inventory': inventory,
                'Strategy': strategy,
                'Cost': cost
            })
        
        return pd.DataFrame(results), total_cost

# Main app
def main():
    st.title("📊 Mandexor Memory Production Planning Dashboard")
    st.markdown("**OATY 3.0 Case Study | Question 3: Production Level Changes**")
    
    # Load data
    demand_data, params = load_case_data()
    planner = ProductionPlanner(demand_data, params)
    
    # Sidebar
    st.sidebar.header("🎛️ Scenario Controls")
    
    scenario = st.sidebar.selectbox(
        "Demand Scenario:",
        ['base', 'optimistic', 'pessimistic', 'volatile'],
        format_func=lambda x: x.upper()
    )
    
    ot_weight = st.sidebar.slider("Overtime Preference (%)", 0, 100, 60) / 100
    sub_weight = 1 - ot_weight
    
    # Calculate
    demand_df = planner.apply_scenario(scenario)
    results_df, total_cost = planner.optimize_strategy(demand_df, ot_weight, sub_weight)
    
    # Key metrics
    st.markdown("---")
    st.subheader("📈 Executive Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Demand", f"{results_df['Demand'].sum():,.0f} units")
    
    with col2:
        shortfall = demand_df[demand_df['Capacity_gap'] > 0]['Capacity_gap'].sum()
        st.metric("Capacity Shortfall", f"{shortfall:,.0f} units")
    
    with col3:
        st.metric("Overtime Production", f"{results_df['Overtime'].sum():,.0f} units")
    
    with col4:
        st.metric("Subcontracted", f"{results_df['Subcontract'].sum():,.0f} units")
    
    # Strategic Recommendations
    st.markdown("---")
    st.subheader("💡 Question 3: How to Change Production Levels")
    
    st.success(f"""
    **Scenario: {scenario.upper()}**
    
    **Immediate Actions (0-1 month):**
    - ±5% forecast change → Monitor only
    - +10% → Activate weekday overtime (up to 2 hrs/day)
    - +15% → Mixed strategy: {ot_weight*100:.0f}% overtime, {sub_weight*100:.0f}% subcontract
    
    **Short-term (1-3 months):**
    - Sustained +15% → Initiate subcontractor negotiations
    - High volatility → Increase safety stock to 10% of demand
    
    **Medium-term (3-6 months):**
    - Jun-Aug low period → Build inventory to {params['warehouse_capacity']:,} units
    - Sustained high demand → Evaluate capacity expansion
    
    **Current Scenario Results:**
    - Total Cost: ${total_cost:,.2f}
    - Cost per Unit: ${total_cost/results_df['Demand'].sum():.2f}
    """)
    
    # Tabs for visualizations
    tab1, tab2, tab3 = st.tabs(["📊 Capacity Analysis", "💰 Cost & Strategy", "📈 Trends"])
    
    with tab1:
        # Demand vs Capacity chart
        fig1 = go.Figure()
        
        fig1.add_trace(go.Scatter(
            x=results_df['Month'], 
            y=results_df['Demand'],
            name='Demand',
            mode='lines+markers',
            line=dict(color='red', width=3)
        ))
        
        fig1.add_trace(go.Scatter(
            x=results_df['Month'],
            y=results_df['Capacity'],
            name='Normal Capacity',
            mode='lines+markers',
            line=dict(color='green', width=3)
        ))
        
        fig1.update_layout(
            title="Monthly Demand vs Capacity",
            xaxis_title="Month",
            yaxis_title="Units",
            hovermode='x unified',
            height=500
        )
        
        st.plotly_chart(fig1, use_container_width=True)
        
        # Gap chart
        fig2 = go.Figure()
        colors = ['red' if x > 0 else 'green' for x in results_df['Gap']]
        
        fig2.add_trace(go.Bar(
            x=results_df['Month'],
            y=results_df['Gap'],
            marker_color=colors,
            name='Capacity Gap'
        ))
        
        fig2.update_layout(
            title="Capacity Gap (Shortfall/Excess)",
            xaxis_title="Month",
            yaxis_title="Gap (Units)",
            height=400
        )
        
        st.plotly_chart(fig2, use_container_width=True)
        
        # Data table
        st.dataframe(results_df, use_container_width=True)
    
    with tab2:
        # Strategy distribution
        strategy_counts = results_df['Strategy'].value_counts()
        
        fig3 = go.Figure(data=[go.Pie(
            labels=strategy_counts.index,
            values=strategy_counts.values,
            hole=0.4
        )])
        
        fig3.update_layout(
            title="Strategy Distribution",
            height=400
        )
        
        st.plotly_chart(fig3, use_container_width=True)
        
        # Cost breakdown
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Total Cost", f"${total_cost:,.2f}")
            st.metric("Overtime Cost", f"${results_df['Overtime'].sum() * 150:,.2f}")
        
        with col2:
            st.metric("Cost per Unit", f"${total_cost/results_df['Demand'].sum():.2f}")
            st.metric("Subcontract Cost", f"${results_df['Subcontract'].sum() * 125:,.2f}")
        
        # Monthly cost
        fig4 = go.Figure()
        fig4.add_trace(go.Bar(
            x=results_df['Month'],
            y=results_df['Cost'],
            marker_color='steelblue'
        ))
        
        fig4.update_layout(
            title="Monthly Cost",
            xaxis_title="Month",
            yaxis_title="Cost ($)",
            height=400
        )
        
        st.plotly_chart(fig4, use_container_width=True)
    
    with tab3:
        # Inventory trend
        fig5 = go.Figure()
        
        fig5.add_trace(go.Scatter(
            x=results_df['Month'],
            y=results_df['Inventory'],
            mode='lines+markers',
            name='Inventory',
            line=dict(color='purple', width=3)
        ))
        
        fig5.add_hline(
            y=params['warehouse_capacity'],
            line_dash="dash",
            line_color="red",
            annotation_text="Warehouse Capacity"
        )
        
        fig5.update_layout(
            title="Inventory Levels",
            xaxis_title="Month",
            yaxis_title="Units",
            height=400
        )
        
        st.plotly_chart(fig5, use_container_width=True)
        
        # Production mix
        fig6 = go.Figure()
        
        fig6.add_trace(go.Scatter(
            x=results_df['Month'],
            y=results_df['Capacity'],
            name='Normal Production',
            mode='lines',
            stackgroup='one',
            fillcolor='lightgreen'
        ))
        
        fig6.add_trace(go.Scatter(
            x=results_df['Month'],
            y=results_df['Overtime'],
            name='Overtime',
            mode='lines',
            stackgroup='one',
            fillcolor='orange'
        ))
        
        fig6.add_trace(go.Scatter(
            x=results_df['Month'],
            y=results_df['Subcontract'],
            name='Subcontract',
            mode='lines',
            stackgroup='one',
            fillcolor='purple'
        ))
        
        fig6.update_layout(
            title="Production Strategy Mix",
            xaxis_title="Month",
            yaxis_title="Units",
            height=400
        )
        
        st.plotly_chart(fig6, use_container_width=True)
    
    # Decision matrix
    st.markdown("---")
    st.subheader("🎯 Decision Support Matrix")
    
    decision_data = {
        'Forecast Change': ['±5%', '±10%', '±15%', '±20%', '±30%+'],
        'Response Time': ['Immediate', '1-2 weeks', '2-4 weeks', '1-2 months', '2-3 months'],
        'Action': [
            'Monitor only',
            'Adjust overtime',
            'Overtime + subcontract',
            'Mixed strategy',
            'Capacity review'
        ],
        'Cost Impact': ['Minimal', 'Low', 'Medium', 'Medium-High', 'High']
    }
    
    st.table(pd.DataFrame(decision_data))
    
    # Export
    st.markdown("---")
    st.subheader("📥 Export Results")
    
    csv = results_df.to_csv(index=False)
    st.download_button(
        "📄 Download Production Plan (CSV)",
        data=csv,
        file_name=f"mandexor_plan_{scenario}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
