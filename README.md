# SET Trading Alert Agent

AI-powered trading analysis agent for Thai stocks (SET). Uses **Claude Code as the brain** — Python scripts collect raw data (prices, technicals, news, sentiment, financials), and Claude Code analyzes everything through slash commands.

> This is **not** a trading bot. It provides data and analysis to support human decision-making.

## How It Works

```
You (via Claude Code)
  │
  ├── /scan              → Scan all watchlist stocks
  ├── /analyze PTT       → Deep analysis on one stock
  ├── /fundamental PTT   → Financial statement deep dive
  ├── /sentiment         → Market-wide sentiment check
  ├── /action_plan       → Daily BUY/SELL/HOLD plan (with risk checks)
  ├── /portfolio         → Track your portfolio, risk & P&L
  ├── /risk              → Portfolio risk dashboard
  ├── /journal           → Trade journal & win rate
  ├── /challenge PTT     → Devil's advocate challenge
  └── /history           → Review past alerts
        │
        ▼
  Python scripts fetch raw data (yfinance, SEC API, Pantip, news)
        │
        ▼
  Claude Code reads the data → analyzes → gives you insights
```

The Python code handles **data collection and computation only**. Claude Code does all the thinking — interpreting indicators, spotting patterns, weighing signals, and explaining what matters.

## Quick Start

### 1. Setup

```bash
git clone <this-repo>
cd Claude-trending

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your keys:
#   LINE_NOTIFY_TOKEN  — for LINE alerts (optional)
#   TELEGRAM_BOT_TOKEN — for Telegram alerts (optional)
#   SEC_API_KEY        — for financial statements (free at api-portal.sec.or.th)
```

### 3. Use with Claude Code

Open the project in Claude Code and use slash commands:

```
/scan                    # Scan all 10 watchlist stocks
/analyze PTT             # Deep analysis on PTT
/fundamental KBANK       # Financial deep dive on KBANK
/sentiment               # What's the market mood?
/action_plan             # Today's BUY/SELL/HOLD recommendations
/portfolio               # Check your portfolio, risk & journal
/portfolio ซื้อ PTT 5000  # Record a purchase
/risk                    # Portfolio risk dashboard
/journal                 # Trade journal & win rate stats
/journal close KBANK 250 # Close a trade at price 250
/challenge KBANK         # Devil's advocate on KBANK
/history                 # Review past alerts
```

## Slash Commands

### `/scan` — Watchlist Scan
Runs price + technical analysis on all stocks in `data/watchlist.json`. Returns a summary table with RSI, MACD, volume signals, and flags unusual activity.

### `/analyze SYMBOL` — Single Stock Deep Analysis
Full analysis of one stock: 6-month price history, technical indicators (RSI, MACD, Bollinger Bands, support/resistance), sentiment from Pantip, and latest news. Claude Code interprets all the data and gives you signals with confidence levels.

### `/fundamental SYMBOL` — Financial Statement Analysis
Fetches 8 quarters from SEC API, computes Piotroski F-Score (0-9), financial ratios (ROE, ROA, D/E, margins), QoQ/YoY growth trends, and assigns a grade (A-F).

### `/sentiment` — Market Sentiment
Scrapes Pantip's Sinthorn room for stock discussions. Identifies most-discussed stocks, overall mood, trending topics, and contrarian signals.

### `/action_plan` — Daily Action Plan
Analyzes all watchlist stocks and generates a table of BUY/SELL/HOLD recommendations with suggested amounts based on conviction scores and position sizing. Includes **risk checks** — BUY signals are automatically blocked or reduced if position limits, deployment caps, or daily loss halt thresholds are violated.

### `/portfolio` — Portfolio Tracker
Track cash balance, stock holdings, P&L, and transaction history. Now includes risk summary and trade journal stats. Record buys/sells in Thai or English:
- `/portfolio` or `/portfolio status` — show portfolio + risk + journal
- `/portfolio ซื้อ PTT 5000` — record buying PTT for 5,000 THB (auto-validates risk limits)
- `/portfolio sell ADVANC 3000` — record selling ADVANC for 3,000 THB

### `/risk` — Risk Dashboard
Portfolio-wide risk monitoring:
- **Portfolio Heat** — sum of (position weight x 20-day volatility). LOW / MEDIUM / HIGH
- **Stop-Loss Alerts** — flags holdings down -15% or more vs avg cost
- **Daily Loss Halt** — if portfolio drops -5% intraday, all BUY orders blocked
- **Position Limits** — max 15% per stock, 50% total deployment cap
- **Sector Concentration** — max 40% in any one sector

### `/journal` — Trade Journal
Track every trade with reasoning, outcome, and lessons learned:
- `/journal` — open trades, win rate, strategy performance
- `/journal close KBANK 250` — close a trade at exit price, record outcome
- `/journal history` — full trade history

Performance metrics: win rate, avg win/loss, profit factor, Kelly fraction (optimal bet size).

### `/challenge SYMBOL` — Consultant / Devil's Advocate
An independent challenge agent that tests your thesis on a stock:
- Runs full analysis + risk checks + trade journal history
- Produces **bear case** (if you're bullish) or **bull case** (if you're bearish)
- Identifies blind spots, data gaps, sector/correlation risks
- Checks past trades on the same symbol for historical patterns
- Delivers a risk-adjusted verdict: **AGREE**, **DISAGREE**, or **MODIFY**

### `/history` — Alert History
Shows past alerts from the last 7 days with performance tracking.

## Running Scripts Directly

You can also run any script directly from the terminal:

```bash
# Fetch price data
python3 agents/data_collector.py --symbol PTT
python3 agents/data_collector.py --all

# Technical analysis
python3 agents/technical_agent.py --symbol PTT

# Scrapers
python3 scrapers/sec_api_client.py --symbol PTT --periods 8
python3 scrapers/pantip_scraper.py --symbol PTT
python3 scrapers/news_scraper.py --symbol PTT

# Fundamental computation
python3 analysis/fundamental.py --symbol PTT
python3 analysis/financial_health.py --symbol PTT

# Portfolio
python3 agents/portfolio_agent.py status
python3 agents/portfolio_agent.py buy --symbol PTT --amount 5000 --price 35.50

# Risk management
python3 analysis/risk_manager.py report           # Full risk dashboard
python3 analysis/risk_manager.py stop-losses       # Check stop-loss alerts
python3 analysis/risk_manager.py check-buy --symbol PTT --amount 30000  # Validate a BUY
python3 analysis/risk_manager.py snapshot          # Record daily portfolio snapshot

# Trade journal
python3 analysis/trade_journal.py status           # Open trades
python3 analysis/trade_journal.py winrate          # Win rate & performance stats
python3 analysis/trade_journal.py strategies       # Performance by strategy
python3 analysis/trade_journal.py history          # Closed trade history

# Action plan (now includes risk checks)
python3 agents/action_plan_agent.py --budget 100000

# Auto-scheduler (runs every 30 min during market hours)
python3 scheduler.py
```

All scripts output JSON, which Claude Code can read and analyze.

## Project Structure

```
Claude-trending/
├── agents/                    # Data collection & processing agents
│   ├── orchestrator.py        # Combines all sub-agent results
│   ├── data_collector.py      # yfinance price/volume fetcher
│   ├── technical_agent.py     # RSI, MACD, Bollinger Bands
│   ├── sentiment_agent.py     # Pantip + Twitter sentiment
│   ├── news_agent.py          # Thai news analysis
│   ├── fundamental_agent.py   # Financial statements + ratios
│   ├── alert_agent.py         # Alert dispatch (LINE/Telegram)
│   ├── action_plan_agent.py   # Daily BUY/SELL/HOLD plan
│   └── portfolio_agent.py     # Portfolio tracking + P&L
├── scrapers/                  # External data fetchers
│   ├── settrade_scraper.py    # Settrade.com (Playwright)
│   ├── sec_api_client.py      # SEC API Portal (REST)
│   ├── set_smart_client.py    # SET SMART marketplace
│   ├── pantip_scraper.py      # Pantip ห้องสินธร
│   ├── twitter_scraper.py     # Twitter/X Thai stocks
│   └── news_scraper.py        # Thai financial news
├── analysis/                  # Pure computation modules
│   ├── technical.py           # Technical indicators
│   ├── thai_sentiment.py      # Thai NLP sentiment
│   ├── volume_analysis.py     # Volume profile, money flow
│   ├── fundamental.py         # Financial ratios, grading
│   ├── financial_health.py    # Piotroski F-Score (0-9)
│   ├── scoring.py             # Composite score (-100 to +100)
│   ├── position_sizing.py     # Position sizing logic
│   ├── risk_manager.py        # Portfolio risk checks & limits
│   └── trade_journal.py       # Trade journal & win rate tracking
├── alerts/                    # Notification delivery
│   ├── line_notify.py         # LINE Notify API
│   ├── telegram_bot.py        # Telegram Bot API
│   └── templates/             # Thai alert message templates
├── config/
│   ├── settings.yaml          # General settings
│   └── thresholds.yaml        # Alert thresholds & scoring weights
├── data/
│   └── watchlist.json         # 10 SET50 stocks to track
├── .claude/commands/          # Claude Code slash commands
├── scheduler.py               # APScheduler (market hours)
├── requirements.txt           # Python dependencies
└── CLAUDE.md                  # Claude Code instructions
```

## Watchlist

Default watchlist (`data/watchlist.json`) tracks 10 SET50 stocks:

| Symbol | Sector | Name |
|--------|--------|------|
| PTT | Energy | ปตท. |
| ADVANC | Technology | แอดวานซ์ อินโฟร์ เซอร์วิส |
| AOT | Transport | ท่าอากาศยานไทย |
| CPALL | Commerce | ซีพี ออลล์ |
| GULF | Energy | กัลฟ์ เอ็นเนอร์จี ดีเวลลอปเมนท์ |
| KBANK | Banking | ธนาคารกสิกรไทย |
| SCB | Banking | ธนาคารไทยพาณิชย์ |
| SCC | Construction | ปูนซิเมนต์ไทย |
| BDMS | Healthcare | กรุงเทพดุสิตเวชการ |
| DELTA | Electronics | เดลต้า อีเลคโทรนิคส์ |

Edit `data/watchlist.json` to track different stocks.

## Scoring System

### Composite Score (-100 to +100)

| Component | Weight |
|-----------|--------|
| Technical | 25% |
| Sentiment | 20% |
| Fundamental | 20% |
| Volume | 15% |
| News | 10% |
| Fund Flow | 10% |

### Alert Thresholds

| Signal | Conditions |
|--------|-----------|
| **BUY** | Composite > 60, RSI < 30, sentiment > 0.3, volume > 2x avg |
| **SELL** | Composite < -60, RSI > 70, sentiment < -0.3 |
| **WATCH** | Volume > 1.5x avg, price move > 3% intraday |

### Piotroski F-Score (0-9)

9 binary criteria covering profitability, capital structure, and efficiency. Score >= 7 is strong, <= 3 is weak.

## Risk Management

Built-in risk rules that automatically enforce portfolio discipline:

| Rule | Threshold | Action |
|------|-----------|--------|
| Max position size | 15% of portfolio per stock | BUY amount reduced or blocked |
| Deployment cap | 50% of portfolio in stocks | New BUY orders blocked |
| Stop-loss | -15% from avg cost | Alert triggered |
| Daily loss halt | -5% portfolio drop intraday | All BUY orders halted |
| Sector concentration | 40% max in one sector | Warning displayed |
| Portfolio heat | Weighted volatility exposure | LOW / MEDIUM / HIGH indicator |

Risk checks run automatically when generating action plans (`/action_plan`) and recording portfolio transactions (`/portfolio buy`). Use `/risk` for a full dashboard.

## Trade Journal

Every trade is automatically recorded with entry/exit data, reasoning, and outcome. The journal tracks:

- **Win rate** — percentage of profitable trades
- **Profit factor** — gross profit / gross loss
- **Kelly fraction** — optimal position size based on historical performance
- **Strategy breakdown** — performance by strategy type

Use `/journal` to view stats or `/journal close SYMBOL PRICE` to close a trade with lessons learned.

## Disclaimer

ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน

This tool provides data and analysis for informational purposes only. It is not investment advice. Always do your own research before making investment decisions.
