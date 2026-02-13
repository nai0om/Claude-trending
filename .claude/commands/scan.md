Scan the entire SET market + watchlist. This runs Market Discovery first, then the detailed watchlist scan.

---

## Step 0: Market Discovery (SET ทั้งตลาด)

### Step 0a: Ensure SET stock list is fresh
Run `python scrapers/set_stock_list.py` to download/refresh the full SET stock list.
This caches to `data/set_all_stocks.json` (auto-refreshes if > 7 days old).

### Step 0b: Screen all SET stocks
Run `python scrapers/market_screener.py --top 10` to batch-screen all ~600 SET stocks.
This produces `data/scans/screener_{date}.json` with categories:
- Top Gainers / Top Losers (1-day price change)
- Volume Spikes (volume > 3x 20-day average)
- Oversold (RSI < 30) / Overbought (RSI > 70)

### Step 0c: Find socially trending stocks
Run `python scrapers/social_trending.py --days 3` to discover trending stocks from social media.
This produces `data/scans/trending_{date}.json` with:
- Stocks mentioned most across Pantip, Twitter, Facebook, news
- Sentiment and engagement per discovered symbol
- New discoveries not in the watchlist

### Step 0d: Present Market Discovery summary

Present the Market Discovery results in this format:

```
## Market Discovery (SET ทั้งตลาด)
| # | Symbol | Sector | Price | Chg% | RSI | Vol Ratio | Signal |
Top Gainers / Top Losers / Volume Spikes / Oversold / Overbought

## Social Trending (ไม่อยู่ใน Watchlist)
| # | Symbol | Mentions | Engagement | Sentiment | Signal |
```

---

## Step 1: Technical Data (Watchlist)
For each stock in data/watchlist.json, fetch price/volume and compute indicators (RSI, MACD, Bollinger Bands).
You can do this via yfinance directly in a single Python script for efficiency, or run per-stock:
1. `python agents/data_collector.py --symbol SYMBOL`
2. `python agents/technical_agent.py --symbol SYMBOL`

## Step 2: Social Sentiment (Search Center API)
Use the Search Center API at http://localhost:4344 to get real social media sentiment:

1. Run `python scrapers/search_center_client.py --action compare --symbols PTT ADVANC AOT CPALL GULF KBANK SCB SCC BDMS DELTA --days 7` — compare all stocks' mentions, engagement, and sentiment in one call
2. For any stock with unusual sentiment (negative > 20% or positive > 50%), run `python agents/sentiment_agent.py --symbol SYMBOL` to get detailed breakdown and top posts

## Step 3: Summary Table
Provide a combined summary table with:
- Symbol | Price | Chg% | RSI | MACD Signal | Vol Ratio | Mentions | Sentiment | Overall Signal

## Step 4: Flags & Alerts
Flag any stocks with unusual signals:
- **Technical**: RSI < 30 or > 70, volume > 2x average, price outside Bollinger Bands
- **Social**: Mention spike > 2x normal, negative sentiment > 20%, extreme positive > 50%
- **Combined**: Technical overbought + bearish sentiment = potential reversal warning

## Step 5: Market Analysis
Provide overall market analysis combining both technical and sentiment data.

## Step 6: Combined Discovery + Watchlist Report
Cross-reference Market Discovery results with watchlist scan:
- Flag any **screener discoveries** (top gainers, volume spikes, oversold) that also appear in the watchlist
- Flag any **socially trending stocks** that overlap with watchlist stocks showing technical signals
- Highlight **new opportunities**: stocks from the screener/trending that are NOT in the watchlist but show strong combined signals (e.g., oversold + bullish trending, or volume spike + high engagement)
- Suggest additions to the watchlist if any non-watchlist stock appears in multiple discovery categories

## Data Persistence (REQUIRED)

After collecting all data, you MUST save results to files:

### Per-stock files: `data/stocks/{SYMBOL}.json`
- If the file already exists, READ it first, then APPEND new entries
- If the file does not exist, create it with the structure below
- Each scan entry includes: date, price, indicators, volume, levels, sentiment, flags, signal

Structure:
```json
{
  "symbol": "SYMBOL",
  "name": "Thai name",
  "sector": "Sector",
  "scans": [
    {
      "date": "YYYY-MM-DD",
      "scanned_at": "ISO timestamp",
      "price": { "close": 0.00, "change_pct": 0.00 },
      "indicators": {
        "rsi": 0.00,
        "macd": 0.0000, "macd_signal": 0.0000, "macd_hist": 0.0000,
        "bb_upper": 0.00, "bb_middle": 0.00, "bb_lower": 0.00
      },
      "volume": { "latest": 0, "avg_20d": 0, "ratio": 0.00 },
      "levels": { "support": 0.00, "resistance": 0.00 },
      "sentiment": {
        "total_mentions": 0,
        "score": 0.00,
        "label": "Bullish/Bearish/Neutral",
        "positive": 0, "neutral": 0, "negative": 0,
        "engagement": 0,
        "confidence": "Low/Medium/High"
      },
      "flags": [],
      "signal": "Overall Signal"
    }
  ],
  "notes": [],
  "alerts": []
}
```

### Scan summary: `data/scans/scan_{YYYY-MM-DD}.json`
- Save a full market snapshot with all stocks' summary data
- Include: market_sentiment, technical and social flags
- Structure:
```json
{
  "scan_date": "YYYY-MM-DD",
  "scanned_at": "ISO timestamp",
  "market_sentiment": "description",
  "stocks_scanned": 10,
  "overbought_count": 0,
  "oversold_count": 0,
  "all_macd_bullish": true,
  "summary": [
    {
      "symbol": "", "close": 0, "rsi": 0, "macd_signal": "",
      "vol_ratio": 0, "mentions": 0, "sentiment_score": 0.00,
      "sentiment_label": "", "signal": ""
    }
  ],
  "flagged": {
    "overbought": [], "oversold": [],
    "high_volume": [], "price_breakout": [],
    "sentiment_bearish": [], "sentiment_bullish": [],
    "mention_spike": []
  }
}
```

IMPORTANT: Always read existing stock files before writing to preserve historical scan data. Never overwrite — always append.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
