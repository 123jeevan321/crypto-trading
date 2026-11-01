# Breaking Money — The AI Trading Arena (Indian Market 2)
> **Build. Simulate. Learn. Repeat. COMPLETE 15-DAY CHALLENGE & SETUP**

A production-grade, paper-only algorithmic trading arena and 15-day challenge platform built for the Indian Stock Market (NSE), adhering strictly to the specifications of the *Breaking Money: The AI Trading Arena Complete Guide*.

---

## 🎯 Architecture & Specifications

- **Virtual Capital**: ₹1,00,000 virtual balance (Zero live financial risk).
- **Duration**: 15 Trading Sessions.
- **Port**: Control Panel Dashboard on `http://127.0.0.1:5003`.
- **Decision Engines (Brains)**:
  1. `Claude Code` (installed CLI via `claude -p "..."`)
  2. `Anthropic API` (`ANTHROPIC_API_KEY` via `.env`)
  3. `Rules Baseline` (Deterministic ORB breakout, 20/50 EMA trend filter, RSI 45-65 momentum, volume expansion)
  4. `Auto Mode` (Smart fallback cascade: Claude Code CLI -> Anthropic API -> Rules Baseline)
- **Institutional Risk Guardrails**:
  - Maximum 20% equity per position (₹20,000 max on ₹1,00,000 capital)
  - Stop-loss: 1.5% | Take-profit: 3.0%
  - Daily Drawdown Limit: 3.0% maximum daily loss cap (trading halts if breached)
  - Session Cutoff: No new entries allowed after 14:45 IST
  - Auto Square-Off: All open positions automatically squared off at 15:15 IST
- **Realistic Market Frictions**:
  - STT (Securities Transaction Tax): 0.025% on intraday sell leg
  - Exchange turnover charges: 0.00345%
  - GST: 18% on exchange turnover charges and brokerage
  - Stamp Duty: 0.003% on buy leg
  - Execution Slippage: 0.05% modeled on entries and exits

---

## 🚀 Quick Launch

### Windows One-Click:
Double-click `START-TRADING.bat` or run:
```cmd
START-TRADING.bat
```
This automatically launches the background server and opens your browser at `http://127.0.0.1:5003`.

### macOS / Linux:
```bash
./setup.sh
./start-trading.command
```

---

## 💻 CLI Commands

Run from the `indian-market-2` directory:

| Command | Description |
| :--- | :--- |
| `python -m arena check` | Evaluates system health, brains (CLI/API/Rules), feed connection, and safety assertion |
| `python -m arena demo` | Runs an offline simulated session using synthetic prices and prints full trade telemetry |
| `python -m arena run` | Launches the live trading engine and the Web Dashboard on port 5003 |
| `python -m arena replay` | Replays a past session bar by bar (`--date YYYY-MM-DD`, `--brain auto`) |
| `python -m arena compete` | Runs a head-to-head competition between Rules Baseline and Claude Engine |
| `python -m arena status` | Displays the current 15-day challenge snapshot, equity, cash, and trade metrics |
| `python -m arena report` | Generates the standalone `reports/results.html` audit report with Chart.js curve |

---

## 📁 Repository Structure

```
indian-market-2/
├── config.toml                 # Challenge, risk profile, friction, and web configurations
├── requirements.txt            # Python dependencies (Flask, yfinance, pandas, pytz)
├── .env.example                # Template for optional ANTHROPIC_API_KEY
├── START-TRADING.bat           # 1-click Windows launcher
├── setup.bat                   # 1-click Windows installer
├── start-trading.command       # macOS launcher
├── setup.sh                    # macOS installer
├── reports/
│   └── results.html            # Interactive 15-day performance report
├── data/
│   └── challenge_state.json    # Challenge persistence
├── arena/
│   ├── config.py               # TOML & environment parser
│   ├── cli.py                  # All CLI subcommands
│   ├── brains/
│   │   ├── base.py             # DecisionEngine abstract class
│   │   ├── rules.py            # Deterministic momentum baseline
│   │   ├── claude_code.py      # Claude CLI subprocess bridge
│   │   ├── anthropic_api.py    # Anthropic Claude 3.5 REST API bridge
│   │   └── auto.py             # Auto-fallback router
│   ├── engine/
│   │   ├── risk_manager.py     # 20% cap, SL/TP bounds, time cutoffs
│   │   ├── simulation.py       # Virtual execution, slippage & NSE charges
│   │   └── challenge.py        # 15-day challenge progression & journal
│   ├── market_data/
│   │   ├── holidays.py         # NSE trading calendar & IST hours
│   │   ├── feed.py             # Yahoo Finance / NSE live quotes feed
│   │   └── synthetic.py        # Synthetic price generator for demo mode
│   └── web/
│       ├── app.py              # Flask server on port 5003
│       ├── templates/
│       │   └── dashboard.html  # Dark institutional control panel
│       └── static/
│           ├── css/arena.css   # Institutional UI styling
│           └── js/arena.js     # Real-time WebSocket / polling client
└── tests/
    └── test_arena.py           # Unit tests
```
