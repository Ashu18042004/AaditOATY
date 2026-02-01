<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mandexor Memory - Production Planning Decision Tree</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .content {
            padding: 40px;
        }
        
        .scenario-section {
            margin-bottom: 50px;
        }
        
        .scenario-header {
            display: flex;
            align-items: center;
            gap: 15px;
            margin-bottom: 25px;
            padding: 20px;
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            border-radius: 15px;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        
        .scenario-header:hover {
            transform: translateX(10px);
        }
        
        .scenario-header .icon {
            font-size: 2em;
        }
        
        .scenario-header .title {
            flex: 1;
        }
        
        .scenario-header .title h2 {
            font-size: 1.8em;
            margin-bottom: 5px;
        }
        
        .scenario-header .title p {
            opacity: 0.9;
            font-size: 0.95em;
        }
        
        .scenario-header .toggle {
            font-size: 1.5em;
            transition: transform 0.3s ease;
        }
        
        .scenario-header.collapsed .toggle {
            transform: rotate(-90deg);
        }
        
        .decision-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .decision-card {
            background: white;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 25px;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .decision-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 5px;
            height: 100%;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
        }
        
        .decision-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0,0,0,0.15);
            border-color: #667eea;
        }
        
        .decision-card .condition {
            font-size: 1.1em;
            font-weight: bold;
            color: #2a5298;
            margin-bottom: 15px;
            padding-left: 30px;
            position: relative;
        }
        
        .decision-card .condition::before {
            content: '🎯';
            position: absolute;
            left: 0;
            font-size: 1.2em;
        }
        
        .decision-card .action {
            background: #f0f7ff;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 1.05em;
            color: #1e3c72;
            border-left: 3px solid #667eea;
        }
        
        .decision-card .action::before {
            content: '▶ ';
            color: #667eea;
            font-weight: bold;
        }
        
        .decision-card .reasoning {
            color: #666;
            font-style: italic;
            padding: 10px;
            background: #fafafa;
            border-radius: 6px;
            font-size: 0.95em;
        }
        
        .decision-card .reasoning::before {
            content: '💡 ';
        }
        
        .trigger-section {
            background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);
            padding: 30px;
            border-radius: 15px;
            margin-top: 30px;
        }
        
        .trigger-section h3 {
            color: white;
            font-size: 1.8em;
            margin-bottom: 20px;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.2);
        }
        
        .trigger-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 15px;
        }
        
        .trigger-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .trigger-card .metric {
            font-weight: bold;
            color: #fa709a;
            font-size: 1.1em;
            margin-bottom: 8px;
        }
        
        .trigger-card .threshold {
            background: #fff3cd;
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            border-left: 3px solid #ffc107;
            font-family: 'Courier New', monospace;
        }
        
        .trigger-card .action {
            color: #666;
            font-size: 0.95em;
        }
        
        .stats-banner {
            background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
            padding: 30px;
            border-radius: 15px;
            margin-bottom: 40px;
            color: white;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        
        .stat-item {
            text-align: center;
            background: rgba(255,255,255,0.2);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }
        
        .stat-item .value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-item .label {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .timeline {
            position: relative;
            padding: 20px 0;
        }
        
        .timeline::before {
            content: '';
            position: absolute;
            left: 50%;
            top: 0;
            bottom: 0;
            width: 4px;
            background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
            transform: translateX(-50%);
        }
        
        .timeline-item {
            display: flex;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .timeline-item:nth-child(even) {
            flex-direction: row-reverse;
        }
        
        .timeline-content {
            flex: 1;
            padding: 20px;
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            margin: 0 20px;
        }
        
        .timeline-marker {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            box-shadow: 0 4px 10px rgba(0,0,0,0.2);
            z-index: 1;
        }
        
        @media (max-width: 768px) {
            .timeline::before {
                left: 20px;
            }
            
            .timeline-item,
            .timeline-item:nth-child(even) {
                flex-direction: row;
            }
            
            .timeline-content {
                margin-left: 40px;
                margin-right: 0;
            }
            
            .header h1 {
                font-size: 1.8em;
            }
            
            .decision-grid,
            .trigger-grid,
            .stats-grid {
                grid-template-columns: 1fr;
            }
        }
        
        .button-group {
            display: flex;
            gap: 15px;
            justify-content: center;
            margin-top: 30px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(102, 126, 234, 0.4);
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(102, 126, 234, 0.6);
        }
        
        .btn-secondary {
            background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
            color: white;
            box-shadow: 0 4px 15px rgba(245, 87, 108, 0.4);
        }
        
        .btn-secondary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(245, 87, 108, 0.6);
        }
        
        .scenario-content {
            max-height: 2000px;
            overflow: hidden;
            transition: max-height 0.5s ease;
        }
        
        .scenario-content.collapsed {
            max-height: 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Mandexor Memory Production Planning</h1>
            <p>Interactive Decision Tree | OATY 3.0 Case Study - Question 3</p>
        </div>
        
        <div class="content">
            <!-- Statistics Banner -->
            <div class="stats-banner">
                <h2 style="text-align: center; margin-bottom: 10px;">📈 Key Performance Metrics (Base Scenario)</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="value">908,110</div>
                        <div class="label">Annual Demand (units)</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">$6.66M</div>
                        <div class="label">Total Cost</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">79,566</div>
                        <div class="label">Overtime Units</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">53,044</div>
                        <div class="label">Subcontracted Units</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">15.7%</div>
                        <div class="label">Capacity Shortfall</div>
                    </div>
                </div>
            </div>
            
            <!-- Immediate Actions Section -->
            <div class="scenario-section">
                <div class="scenario-header" onclick="toggleSection(this)">
                    <div class="icon">⚡</div>
                    <div class="title">
                        <h2>Immediate Actions</h2>
                        <p>0-1 Month Horizon | Rapid Response Protocols</p>
                    </div>
                    <div class="toggle">▼</div>
                </div>
                <div class="scenario-content">
                    <div class="decision-grid">
                        <div class="decision-card">
                            <div class="condition">Forecast change ±5%</div>
                            <div class="action">Monitor closely, no immediate production changes</div>
                            <div class="reasoning">Within normal forecast error range. Historical data shows ±5% is typical variance.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast change +10%</div>
                            <div class="action">Activate weekday overtime planning (up to 2 hrs/day)</div>
                            <div class="reasoning">Can handle up to 8.8% of annual demand via overtime. Cost: 150% of normal rate. Requires 4-week union notice.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast change -10%</div>
                            <div class="action">Reduce overtime, build strategic inventory if below target</div>
                            <div class="reasoning">Utilize excess capacity for inventory building. Inventory holding cost: 20% annually (1.67% monthly).</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast change +15%</div>
                            <div class="action">Emergency planning meeting + overtime + subcontractor alert</div>
                            <div class="reasoning">Exceeds overtime capacity alone. Requires mixed strategy to meet demand without excessive inventory depletion.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast volatility >20%</div>
                            <div class="action">Activate safety stock protocol + weekly forecast reviews</div>
                            <div class="reasoning">High uncertainty requires buffer. Target: 10% of monthly demand as safety stock (~7,500 units).</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast accuracy <80%</div>
                            <div class="action">Escalate to Marketing Division + improve forecasting process</div>
                            <div class="reasoning">Poor forecasts drive unnecessary costs. Root cause analysis required to improve accuracy.</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Short-term Adjustments Section -->
            <div class="scenario-section">
                <div class="scenario-header" onclick="toggleSection(this)">
                    <div class="icon">🎯</div>
                    <div class="title">
                        <h2>Short-term Adjustments</h2>
                        <p>1-3 Month Horizon | Tactical Planning</p>
                    </div>
                    <div class="toggle">▼</div>
                </div>
                <div class="scenario-content">
                    <div class="decision-grid">
                        <div class="decision-card">
                            <div class="condition">Sustained demand increase >15% for 2+ months</div>
                            <div class="action">Initiate subcontractor negotiations and qualification</div>
                            <div class="reasoning">Subcontracting handled 5.8% of annual demand in base scenario. Cost: 125% of factory cost. Lead time: 2-4 weeks for qualification.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Forecast volatility >20%</div>
                            <div class="action">Increase safety inventory to 10% of monthly demand</div>
                            <div class="reasoning">Current max inventory: 6,000 units. Warehouse capacity: 20,000 units. Buffer absorbs forecast errors.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Capacity utilization >95% for 2+ months</div>
                            <div class="action">Mixed strategy: 60% overtime, 40% subcontracting</div>
                            <div class="reasoning">Optimal cost balance based on analysis. Pure overtime unsustainable; pure subcontracting too expensive.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Peak season approaching (Oct-Dec)</div>
                            <div class="action">Pre-build inventory in Sep-Oct + secure subcontractor commitments</div>
                            <div class="reasoning">December demand: 24,000 units/week vs 16,500 capacity. Requires 30,000 additional units production.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Subcontractor quality issues</div>
                            <div class="action">Increase internal overtime + qualify backup subcontractor</div>
                            <div class="reasoning">Quality reputation critical for PC range customers. Cannot compromise on reliability.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Union resistance to overtime</div>
                            <div class="action">Negotiate incentive package + explore temporary workers</div>
                            <div class="reasoning">Labor relations good historically. Win-win approach better than confrontation.</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Medium-term Planning Section -->
            <div class="scenario-section">
                <div class="scenario-header" onclick="toggleSection(this)">
                    <div class="icon">🗓️</div>
                    <div class="title">
                        <h2>Medium-term Planning</h2>
                        <p>3-6 Month Horizon | Strategic Initiatives</p>
                    </div>
                    <div class="toggle">▼</div>
                </div>
                <div class="scenario-content">
                    <div class="decision-grid">
                        <div class="decision-card">
                            <div class="condition">Low-demand periods (Jun-Aug)</div>
                            <div class="action">Build strategic inventory up to warehouse capacity</div>
                            <div class="reasoning">Warehouse capacity: 20,000 units. Summer demand: 15,000 units/week. Excess capacity: 6,000-10,500 units/month.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Sustained high demand >3 months</div>
                            <div class="action">Evaluate capacity expansion or additional shift</div>
                            <div class="reasoning">Better economics than prolonged overtime/subcontracting. Break-even analysis shows payback in 18-24 months.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Subcontracting >20% for 3+ months</div>
                            <div class="action">Business case for permanent capacity increase</div>
                            <div class="reasoning">20% subcontracting = ~180,000 units/year × $125/unit = $22.5M. New line investment: ~$15M with 12-month ROI.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Technology shift imminent</div>
                            <div class="action">Flexible capacity strategy + minimize inventory build</div>
                            <div class="reasoning">Inventory can lose value overnight with tech changes. Maximize flexibility, minimize committed inventory.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Market share growth opportunity</div>
                            <div class="action">Accelerate capacity expansion + secure long-term subcontract</div>
                            <div class="reasoning">Top-end PC manufacturers willing to pay premium for Mandexor reliability. Capacity constraint limits growth.</div>
                        </div>
                        
                        <div class="decision-card">
                            <div class="condition">Seasonal pattern changes</div>
                            <div class="action">Revise inventory build plan + adjust workforce scheduling</div>
                            <div class="reasoning">Traditional Aug low (60% of Dec peak) may shift with e-commerce growth. Monitor and adapt.</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Trigger Points Section -->
            <div class="trigger-section">
                <h3>🚨 Trigger Points for Strategy Changes</h3>
                <div class="trigger-grid">
                    <div class="trigger-card">
                        <div class="metric">⚙️ Capacity Utilization</div>
                        <div class="threshold">>95% for 2 consecutive months</div>
                        <div class="action"><strong>Action:</strong> Activate overtime protocol</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">📊 Forecast Variance</div>
                        <div class="threshold">>±7,568 units (±10% monthly)</div>
                        <div class="action"><strong>Action:</strong> Convene production planning meeting</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">📦 Inventory Level</div>
                        <div class="threshold"><3,784 units (5% of monthly demand)</div>
                        <div class="action"><strong>Action:</strong> Increase production immediately</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">🏭 Subcontracting Usage</div>
                        <div class="threshold">>20% of monthly production for 3+ months</div>
                        <div class="action"><strong>Action:</strong> Evaluate permanent capacity increase</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">💰 Cost per Unit</div>
                        <div class="threshold">>$10/unit average</div>
                        <div class="action"><strong>Action:</strong> Strategy optimization required</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">🎯 Forecast Accuracy</div>
                        <div class="threshold"><80% accuracy</div>
                        <div class="action"><strong>Action:</strong> Improve forecasting process</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">⏰ Overtime Hours</div>
                        <div class="threshold">>10% of total hours for 3+ months</div>
                        <div class="action"><strong>Action:</strong> Review workforce strategy</div>
                    </div>
                    
                    <div class="trigger-card">
                        <div class="metric">📈 Warehouse Utilization</div>
                        <div class="threshold">>90% of capacity (18,000 units)</div>
                        <div class="action"><strong>Action:</strong> Reduce inventory build or expand storage</div>
                    </div>
                </div>
            </div>
            
            <!-- Decision Timeline -->
            <div class="scenario-section" style="margin-top: 50px;">
                <h2 style="text-align: center; color: #1e3c72; margin-bottom: 30px;">⏱️ Decision Response Timeline</h2>
                <div class="timeline">
                    <div class="timeline-item">
                        <div class="timeline-marker">0h</div>
                        <div class="timeline-content">
                            <h3>Forecast Change Detected</h3>
                            <p><strong>Immediate:</strong> Assess magnitude (±5%, ±10%, ±15%+)</p>
                            <p><strong>Action:</strong> Alert production planning team</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-marker">24h</div>
                        <div class="timeline-content">
                            <h3>Initial Analysis Complete</h3>
                            <p><strong>Decision:</strong> Monitor only OR activate response protocol</p>
                            <p><strong>Criteria:</strong> Change magnitude, trend, forecast confidence</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-marker">1w</div>
                        <div class="timeline-content">
                            <h3>Tactical Plan Developed</h3>
                            <p><strong>For +10% change:</strong> Overtime planning begins</p>
                            <p><strong>For +15% change:</strong> Mixed strategy activation</p>
                            <p><strong>Union notice:</strong> 4-week lead time for changes</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-marker">2w</div>
                        <div class="timeline-content">
                            <h3>Subcontractor Engagement</h3>
                            <p><strong>If sustained +15%:</strong> Qualification process starts</p>
                            <p><strong>Lead time:</strong> 2-4 weeks for new subcontractors</p>
                            <p><strong>Cost:</strong> 125% of factory cost</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-marker">1m</div>
                        <div class="timeline-content">
                            <h3>Strategy Execution</h3>
                            <p><strong>Overtime active:</strong> Up to 2 hrs/day weekday</p>
                            <p><strong>Subcontracting:</strong> First deliveries if qualified</p>
                            <p><strong>Inventory:</strong> Strategic build/depletion as planned</p>
                        </div>
                    </div>
                    
                    <div class="timeline-item">
                        <div class="timeline-marker">3m</div>
                        <div class="timeline-content">
                            <h3>Strategic Review</h3>
                            <p><strong>If sustained:</strong> Capacity expansion evaluation</p>
                            <p><strong>If temporary:</strong> Plan transition back to normal</p>
                            <p><strong>Metrics:</strong> Cost/unit, forecast accuracy, customer satisfaction</p>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Action Buttons -->
            <div class="button-group">
                <button class="btn btn-primary" onclick="expandAll()">📖 Expand All Sections</button>
                <button class="btn btn-secondary" onclick="collapseAll()">📕 Collapse All Sections</button>
                <button class="btn btn-primary" onclick="window.print()">🖨️ Print Decision Tree</button>
            </div>
        </div>
    </div>
    
    <script>
        function toggleSection(header) {
            const content = header.nextElementSibling;
            header.classList.toggle('collapsed');
            content.classList.toggle('collapsed');
        }
        
        function expandAll() {
            document.querySelectorAll('.scenario-header').forEach(header => {
                header.classList.remove('collapsed');
                header.nextElementSibling.classList.remove('collapsed');
            });
        }
        
        function collapseAll() {
            document.querySelectorAll('.scenario-header').forEach(header => {
                header.classList.add('collapsed');
                header.nextElementSibling.classList.add('collapsed');
            });
        }
        
        // Add smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    </script>
</body>
</html>
