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
  ├── /action_plan       → Daily BUY/SELL/HOLD plan
  ├── /portfolio         → Track your portfolio & P&L
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
/portfolio               # Check your portfolio
/portfolio ซื้อ PTT 5000  # Record a purchase
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
Analyzes all watchlist stocks and generates a table of BUY/SELL/HOLD recommendations with suggested amounts based on conviction scores and position sizing.

### `/portfolio` — Portfolio Tracker
Track cash balance, stock holdings, P&L, and transaction history. Record buys/sells in Thai or English:
- `/portfolio` or `/portfolio status` — show current portfolio
- `/portfolio ซื้อ PTT 5000` — record buying PTT for 5,000 THB
- `/portfolio sell ADVANC 3000` — record selling ADVANC for 3,000 THB

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

# Action plan
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
│   └── position_sizing.py     # Position sizing logic
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

## Disclaimer

ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน

This tool provides data and analysis for informational purposes only. It is not investment advice. Always do your own research before making investment decisions.
