{
  "immediate_actions": [
    {
      "condition": "Forecast change \u00b15%",
      "action": "Monitor closely, no immediate production changes",
      "reasoning": "Within normal forecast error range"
    },
    {
      "condition": "Forecast change +10%",
      "action": "Activate weekday overtime planning (up to 2 hrs/day)",
      "reasoning": "Can handle up to 8.8% of annual demand via overtime"
    },
    {
      "condition": "Forecast change -10%",
      "action": "Reduce overtime, build strategic inventory if below target",
      "reasoning": "Utilize excess capacity for inventory building"
    }
  ],
  "short_term_adjustments": [
    {
      "condition": "Sustained demand increase >15% for 2+ months",
      "action": "Initiate subcontractor negotiations and qualification",
      "reasoning": "Subcontracting handled 5.8% of demand"
    },
    {
      "condition": "Forecast volatility >20%",
      "action": "Increase safety inventory to 10% of monthly demand",
      "reasoning": "Current max inventory: 6,000 units"
    }
  ],
  "medium_term_planning": [
    {
      "condition": "Low-demand periods (Jun-Aug)",
      "action": "Build strategic inventory up to warehouse capacity",
      "reasoning": "Warehouse capacity: 20,000 units"
    },
    {
      "condition": "Sustained high demand >3 months",
      "action": "Evaluate capacity expansion or additional shift",
      "reasoning": "Better economics than prolonged overtime/subcontracting"
    }
  ],
  "trigger_points": [
    {
      "metric": "Capacity utilization",
      "threshold": ">95% for 2 consecutive months",
      "action": "Activate overtime protocol"
    },
    {
      "metric": "Forecast variance",
      "threshold": ">\u00b17,568 units",
      "action": "Convene production planning meeting"
    },
    {
      "metric": "Inventory level",
      "threshold": "<3,784 units (5% of monthly demand)",
      "action": "Increase production immediately"
    },
    {
      "metric": "Subcontracting usage",
      "threshold": ">20% of monthly production for 3+ months",
      "action": "Evaluate permanent capacity increase"
    }
  ]
}
