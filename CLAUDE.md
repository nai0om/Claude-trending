# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered trading alert agent for Thai stocks (SET). Claude Code serves as the CLI orchestrator/brain that analyzes data from multiple sources (technical, sentiment, fundamental, news) and sends alerts via LINE/Telegram. This is **not** a trading bot — it provides analysis to support human decision-making.

## Tech Stack

- **Runtime**: Python 3.11+ with virtualenv (`venv/`)
- **LLM**: Claude Sonnet 4.5 via Anthropic API
- **Web Scraping**: Playwright (chromium) + BeautifulSoup4
- **Stock Data**: yfinance (`.BK` suffix for SET tickers, e.g., `PTT.BK`)
- **Technical Analysis**: pandas-ta (RSI, MACD, Bollinger Bands)
- **Thai NLP**: WangchanBERTa / PyThaiNLP for sentiment analysis
- **Financial Data**: SEC API Portal (free, requires API key from api-portal.sec.or.th)
- **Database**: SQLite for alerts history, sentiment cache, financial data
- **Alerts**: LINE Notify + Telegram Bot
- **Scheduler**: APScheduler / cron (every 30 min, Mon-Fri 9:30-16:30)

## Build & Run Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Required env vars
export ANTHROPIC_API_KEY="sk-ant-..."
export LINE_NOTIFY_TOKEN="..."
export TELEGRAM_BOT_TOKEN="..."
export SEC_API_KEY="..."

# Run individual agents
python agents/data_collector.py --symbol PTT      # or --all
python agents/technical_agent.py --symbol PTT
python agents/sentiment_agent.py --symbol PTT
python agents/fundamental_agent.py --symbol PTT   # --quick for scan mode
python agents/news_agent.py --symbol PTT
python agents/orchestrator.py --mode analyze --symbol PTT
python agents/orchestrator.py --mode scan          # full watchlist scan

# Scrapers
python scrapers/sec_api_client.py --symbol PTT --periods 8
python scrapers/settrade_scraper.py
python scrapers/pantip_scraper.py
python scrapers/twitter_scraper.py

# Analysis modules
python analysis/fundamental.py --symbol PTT
python analysis/financial_health.py --symbol PTT   # Piotroski F-Score

# Scheduler (auto-run during market hours)
python scheduler.py
```

## Architecture

### Data Flow

```
Data Sources → Scrapers → Agents (analyze) → Orchestrator (combine) → Scoring → Alert
```

1. **Scrapers** (`scrapers/`) fetch raw data from external sources (settrade, SEC API, Pantip, Twitter, news sites)
2. **Agents** (`agents/`) process and analyze data — each agent is independent and handles one domain
3. **Analysis modules** (`analysis/`) contain the computation logic (indicators, scoring, NLP)
4. **Orchestrator** (`agents/orchestrator.py`) combines all agent outputs into a composite score and decides whether to trigger alerts
5. **Alert system** (`alerts/`) formats and delivers notifications via LINE/Telegram using templates from `alerts/templates/`

### Key Agents

| Agent | Role |
|-------|------|
| `orchestrator.py` | Combines all sub-agent results, computes composite score, triggers alerts |
| `data_collector.py` | Fetches price/volume data from SET via yfinance |
| `technical_agent.py` | Computes RSI, MACD, Bollinger Bands, support/resistance |
| `sentiment_agent.py` | Analyzes Thai social media sentiment (Pantip, Twitter) |
| `news_agent.py` | Analyzes Thai/international news impact |
| `fundamental_agent.py` | Analyzes financial statements, ratios, F-Score |
| `alert_agent.py` | Decides and sends alerts |

### Composite Scoring System (-100 to +100)

| Component | Weight |
|-----------|--------|
| Technical | 25% |
| Sentiment | 20% |
| Volume | 15% |
| Fundamental | 20% |
| News | 10% |
| Fund Flow | 10% |

**Fundamental sub-scores**: Profitability (30%), Financial Health (25%), Cash Flow (20%), Valuation (15%), Piotroski F-Score (10%).

### Alert Thresholds (defined in `config/thresholds.yaml`)

- **BUY**: composite > 60, RSI < 30, sentiment > 0.3, volume > 2x avg, F-Score >= 7
- **SELL**: composite < -60, RSI > 70, sentiment < -0.3, declining profits QoQ
- **WATCH**: volume > 1.5x avg, social mention spike > 3x, price move > 3% intraday
- **FUNDAMENTAL ALERT**: new financials released + profit growth > 20% YoY + safe D/E

### Piotroski F-Score (0-9)

Calculated in `analysis/financial_health.py`. Score >= 7 is strong, <= 3 is weak. Nine binary criteria covering profitability (ROA, operating CF, ROA delta, CF quality), capital structure (leverage, liquidity, dilution), and efficiency (margin, turnover).

## Configuration

- `data/watchlist.json` — tracked stock symbols and sectors
- `config/settings.yaml` — general settings
- `config/thresholds.yaml` — alert trigger thresholds
- `data/*.db` — SQLite databases (alerts history, sentiment cache, financial data)

## Slash Commands

- `/scan` — scan entire watchlist (all agents, quick fundamental)
- `/analyze SYMBOL` — deep single-stock analysis (technical + sentiment + fundamental)
- `/fundamental SYMBOL` — deep financial statement analysis (8 quarters, F-Score, valuation, grade A-F)
- `/sentiment` — market-wide sentiment overview
- `/history` — alert history (last 7 days)

## Important Constraints

- Never recommend buying or selling directly — provide data for human decision-making only
- Always show confidence level (Low/Medium/High) on alerts
- Always cite data sources
- Fundamental analysis must compare at least 3 quarters
- All alert messages must include the disclaimer: "ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน"

## Development Phases

1. **MVP**: yfinance data + basic technicals (RSI, MACD) + LINE alerts + slash commands
2. **Fundamental**: SEC API client + financial ratios + F-Score + Claude LLM analysis + grade system
3. **Sentiment**: Pantip/Twitter scrapers + Thai news + WangchanBERTa
4. **Smart Alerts**: Composite scoring + volume/fund flow + backtesting + confidence calibration
5. **Advanced**: Pattern recognition + sector rotation + peer comparison + dashboard
