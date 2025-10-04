"""
Simple static HTML dashboard builder for metrics visualization.

Generates HTML dashboard from reporter JSON artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LLM Beta Testing Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            margin-bottom: 10px;
        }}
        .subtitle {{
            color: #666;
            margin-bottom: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
        }}
        .metric-card h3 {{
            font-size: 14px;
            opacity: 0.9;
            margin-bottom: 10px;
        }}
        .metric-card .value {{
            font-size: 32px;
            font-weight: bold;
        }}
        .sessions-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        .sessions-table th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #333;
            border-bottom: 2px solid #dee2e6;
        }}
        .sessions-table td {{
            padding: 12px;
            border-bottom: 1px solid #dee2e6;
        }}
        .sessions-table tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}
        .badge-success {{
            background: #d4edda;
            color: #155724;
        }}
        .badge-danger {{
            background: #f8d7da;
            color: #721c24;
        }}
        .chart {{
            margin-top: 30px;
        }}
        .bar-chart {{
            display: flex;
            align-items: flex-end;
            height: 200px;
            border-bottom: 2px solid #dee2e6;
            border-left: 2px solid #dee2e6;
            padding-left: 10px;
            gap: 10px;
        }}
        .bar {{
            flex: 1;
            background: #667eea;
            min-height: 10px;
            position: relative;
            display: flex;
            flex-direction: column;
            justify-content: flex-end;
            align-items: center;
        }}
        .bar-value {{
            position: absolute;
            top: -25px;
            font-size: 12px;
            font-weight: 600;
        }}
        .bar-label {{
            margin-top: 5px;
            font-size: 11px;
            text-align: center;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🧪 LLM Beta Testing Dashboard</h1>
        <p class="subtitle">Generated: {generated_at}</p>
        
        <div class="metrics-grid">
            {metric_cards}
        </div>
        
        <div class="chart">
            <h2>Latency Distribution (p50, p95)</h2>
            <div class="bar-chart">
                {latency_bars}
            </div>
        </div>
        
        <h2 style="margin-top: 40px;">Recent Sessions</h2>
        <table class="sessions-table">
            <thead>
                <tr>
                    <th>Session ID</th>
                    <th>Persona</th>
                    <th>Version</th>
                    <th>TSR</th>
                    <th>Latency (p50)</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {session_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""


def build_dashboard(reports_dir: str = "reports", output_path: str = "dashboards/out/index.html") -> None:
    """
    Build HTML dashboard from report JSON files.
    
    Args:
        reports_dir: Directory containing report JSON files
        output_path: Path to save the HTML dashboard
    """
    reports_path = Path(reports_dir)
    
    if not reports_path.exists():
        print(f"Reports directory {reports_dir} not found")
        return
    
    # Load all report JSON files
    reports: list[dict[str, Any]] = []
    for json_file in reports_path.glob("*.json"):
        # Skip diff reports
        if json_file.stem.startswith("diff_"):
            continue
        
        with open(json_file) as f:
            reports.append(json.load(f))
    
    if not reports:
        print("No reports found")
        return
    
    # Calculate aggregate metrics
    total_sessions = len(reports)
    avg_tsr = sum(r["metrics"]["task_success_rate"] for r in reports) / total_sessions
    avg_latency_p50 = sum(r["metrics"]["latency"]["p50"] for r in reports) / total_sessions
    avg_latency_p95 = sum(r["metrics"]["latency"]["p95"] for r in reports) / total_sessions
    
    # Build metric cards
    metric_cards_html = f"""
    <div class="metric-card">
        <h3>Total Sessions</h3>
        <div class="value">{total_sessions}</div>
    </div>
    <div class="metric-card">
        <h3>Avg Task Success Rate</h3>
        <div class="value">{avg_tsr:.1%}</div>
    </div>
    <div class="metric-card">
        <h3>Avg Latency (p50)</h3>
        <div class="value">{avg_latency_p50:.2f}s</div>
    </div>
    <div class="metric-card">
        <h3>Avg Latency (p95)</h3>
        <div class="value">{avg_latency_p95:.2f}s</div>
    </div>
    """
    
    # Build latency bars
    max_lat = max(avg_latency_p50, avg_latency_p95, 2.0)
    p50_height = (avg_latency_p50 / max_lat) * 100
    p95_height = (avg_latency_p95 / max_lat) * 100
    
    latency_bars_html = f"""
    <div class="bar" style="height: {p50_height}%;">
        <span class="bar-value">{avg_latency_p50:.2f}s</span>
    </div>
    <div class="bar" style="height: {p95_height}%;">
        <span class="bar-value">{avg_latency_p95:.2f}s</span>
    </div>
    """
    latency_bars_html += '<div class="bar-label">p50</div><div class="bar-label">p95</div>'
    
    # Build session rows
    session_rows_html = ""
    for report in sorted(reports, key=lambda r: r.get("generated_at", ""), reverse=True)[:10]:
        session_id = report["session_id"][:16]
        persona = report["metadata"].get("persona_name", "Unknown")
        version = report["metadata"].get("version", "N/A")
        tsr = report["metrics"]["task_success_rate"]
        latency_p50 = report["metrics"]["latency"]["p50"]
        status = report["summary"]["pass_rate"]
        
        status_badge = "badge-success" if status > 0.8 else "badge-danger"
        status_text = f"{status:.0%}"
        
        session_rows_html += f"""
        <tr>
            <td><code>{session_id}</code></td>
            <td>{persona}</td>
            <td>{version}</td>
            <td>{tsr:.1%}</td>
            <td>{latency_p50:.3f}s</td>
            <td><span class="badge {status_badge}">{status_text}</span></td>
        </tr>
        """
    
    # Generate HTML
    html = HTML_TEMPLATE.format(
        generated_at=reports[0].get("generated_at", "Unknown"),
        metric_cards=metric_cards_html,
        latency_bars=latency_bars_html,
        session_rows=session_rows_html,
    )
    
    # Save
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, "w") as f:
        f.write(html)
    
    print(f"✅ Dashboard generated: {output}")


if __name__ == "__main__":
    import sys
    reports_dir = sys.argv[1] if len(sys.argv) > 1 else "reports"
    build_dashboard(reports_dir)

