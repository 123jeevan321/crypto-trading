"""
Arena Report Generator: Generates standalone interactive HTML reports (reports/results.html)
with Chart.js equity curve, key performance metrics, and complete trade audit logs.
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from arena.engine.challenge import ChallengeManager

logger = logging.getLogger("arena.reports")

REPORT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "reports", "results.html")

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Trading Arena — 15-Day Challenge Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {
            --bg-dark: #0a0e17;
            --card-bg: #111827;
            --accent-green: #00f298;
            --accent-red: #ff3366;
            --accent-cyan: #00d2ff;
            --border-color: #1f293d;
            --text-main: #f3f4f6;
            --text-dim: #9ca3af;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        body { background: var(--bg-dark); color: var(--text-main); padding: 24px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid var(--border-color); padding-bottom: 16px; margin-bottom: 24px; }
        .badge { background: rgba(0, 242, 152, 0.15); color: var(--accent-green); padding: 4px 12px; border-radius: 9999px; font-weight: bold; font-size: 0.85rem; border: 1px solid var(--accent-green); }
        .kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .kpi-card { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; }
        .kpi-title { color: var(--text-dim); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
        .kpi-val { font-size: 1.8rem; font-weight: 800; }
        .kpi-val.positive { color: var(--accent-green); }
        .kpi-val.negative { color: var(--accent-red); }
        .chart-box { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; margin-bottom: 24px; }
        table { width: 100%; border-collapse: collapse; margin-top: 12px; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid var(--border-color); font-size: 0.9rem; }
        th { background: #161f30; color: var(--text-dim); font-size: 0.8rem; text-transform: uppercase; }
        .tag-buy { color: var(--accent-green); font-weight: bold; }
        .tag-sell { color: var(--accent-red); font-weight: bold; }
        .card-table { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 12px; padding: 20px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1 style="font-size: 1.8rem; font-weight: 900; letter-spacing: -0.02em;">BREAKING MONEY / AI TRADING ARENA</h1>
                <p style="color: var(--text-dim); font-size: 0.9rem;">15-Day Challenge Audit & Performance Verification Report</p>
            </div>
            <div>
                <span class="badge">STATUS: {{ status }} (Day {{ current_day }}/{{ target_days }})</span>
            </div>
        </div>

        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-title">Current Equity</div>
                <div class="kpi-val {{ equity_class }}">₹{{ current_equity }}</div>
                <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Initial: ₹{{ initial_capital }}</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Total Return (ROI)</div>
                <div class="kpi-val {{ roi_class }}">{{ roi_pct }}%</div>
                <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Nifty Benchmark: +{{ nifty_return }}%</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Win Rate</div>
                <div class="kpi-val">{{ win_rate_pct }}%</div>
                <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">{{ winning_trades }} Wins / {{ total_trades }} Trades</div>
            </div>
            <div class="kpi-card">
                <div class="kpi-title">Max Drawdown</div>
                <div class="kpi-val negative">{{ max_drawdown_pct }}%</div>
                <div style="font-size: 0.8rem; color: var(--text-dim); margin-top: 4px;">Risk Cap: 3.0% daily</div>
            </div>
        </div>

        <div class="chart-box">
            <h3 style="margin-bottom: 16px; font-size: 1.1rem;">Challenge Equity Progression vs Starting Capital</h3>
            <canvas id="equityChart" height="90"></canvas>
        </div>

        <div class="card-table">
            <h3 style="margin-bottom: 12px; font-size: 1.1rem;">Trade Journal & Regulatory Audit</h3>
            <table>
                <thead>
                    <tr>
                        <th>Date & Time</th>
                        <th>Symbol</th>
                        <th>Side</th>
                        <th>Qty</th>
                        <th>Entry</th>
                        <th>Exit</th>
                        <th>Friction & Taxes</th>
                        <th>Net P&L</th>
                        <th>Engine & Rationale</th>
                    </tr>
                </thead>
                <tbody>
                    {{ trade_rows }}
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const ctx = document.getElementById('equityChart').getContext('2d');
        const labels = {{ chart_labels | safe }};
        const equityData = {{ chart_data | safe }};

        new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Virtual Portfolio Equity (₹)',
                    data: equityData,
                    borderColor: '#00f298',
                    backgroundColor: 'rgba(0, 242, 152, 0.08)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.2
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' } },
                    y: { grid: { color: '#1f293d' }, ticks: { color: '#9ca3af' } }
                }
            }
        });
    </script>
</body>
</html>
"""

def generate_report(challenge_manager: Optional[ChallengeManager] = None) -> str:
    """Generate the static results.html report."""
    cm = challenge_manager or ChallengeManager()
    state = cm.state
    metrics = state.get("metrics", {})

    trades = state.get("trade_journal", [])
    trade_rows = ""

    if not trades:
        trade_rows = '<tr><td colspan="9" style="text-align:center; color: #9ca3af; padding: 24px;">No closed trades recorded yet.</td></tr>'
    else:
        for t in reversed(trades):
            side_cls = "tag-buy" if t.get("side") == "BUY" else "tag-sell"
            pnl_cls = "color: #00f298; font-weight: bold;" if t.get("net_pnl", 0) >= 0 else "color: #ff3366; font-weight: bold;"
            trade_rows += f"""
            <tr>
                <td>{t.get('close_time', t.get('entry_time', '-'))}</td>
                <td><strong>{t.get('symbol')}</strong></td>
                <td><span class="{side_cls}">{t.get('side')}</span></td>
                <td>{t.get('quantity')}</td>
                <td>₹{t.get('entry_price', 0):.2f}</td>
                <td>₹{t.get('close_price', 0):.2f}</td>
                <td style="color:#9ca3af;">₹{t.get('charges', 0):.2f}</td>
                <td style="{pnl_cls}">₹{t.get('net_pnl', 0):.2f}</td>
                <td style="font-size:0.8rem; color:#9ca3af;">{t.get('engine_name', 'Auto')}: {t.get('close_reason', '')}</td>
            </tr>
            """

    # Equity chart data
    chart_labels = ["Day 0"]
    chart_data = [state.get("initial_capital", 100000.0)]
    for hist in state.get("daily_history", []):
        chart_labels.append(f"Day {hist.get('day')} ({hist.get('date')})")
        chart_data.append(hist.get("end_equity"))

    if len(chart_data) == 1:
        chart_labels.append(f"Day {state.get('current_day', 1)} (Current)")
        chart_data.append(state.get("current_equity", 100000.0))

    cur_eq = state.get("current_equity", 100000.0)
    init_cap = state.get("initial_capital", 100000.0)
    roi_pct = metrics.get("roi_pct", 0.0)

    html = HTML_TEMPLATE
    html = html.replace("{{ status }}", str(state.get("status", "NOT_STARTED")))
    html = html.replace("{{ current_day }}", str(state.get("current_day", 1)))
    html = html.replace("{{ target_days }}", str(state.get("target_days", 15)))
    html = html.replace("{{ current_equity }}", f"{cur_eq:,.2f}")
    html = html.replace("{{ initial_capital }}", f"{init_cap:,.2f}")
    html = html.replace("{{ equity_class }}", "positive" if cur_eq >= init_cap else "negative")
    html = html.replace("{{ roi_pct }}", f"{roi_pct:+.2f}")
    html = html.replace("{{ roi_class }}", "positive" if roi_pct >= 0 else "negative")
    html = html.replace("{{ nifty_return }}", f"{metrics.get('nifty_benchmark_return_pct', 0.0):.2f}")
    html = html.replace("{{ win_rate_pct }}", f"{metrics.get('win_rate_pct', 0.0):.1f}")
    html = html.replace("{{ winning_trades }}", str(metrics.get("winning_trades", 0)))
    html = html.replace("{{ total_trades }}", str(metrics.get("total_trades", 0)))
    html = html.replace("{{ max_drawdown_pct }}", f"{metrics.get('max_drawdown_pct', 0.0):.2f}")
    html = html.replace("{{ trade_rows }}", trade_rows)
    html = html.replace("{{ chart_labels | safe }}", json.dumps(chart_labels))
    html = html.replace("{{ chart_data | safe }}", json.dumps(chart_data))

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info("Report written to %s", REPORT_PATH)
    return REPORT_PATH
