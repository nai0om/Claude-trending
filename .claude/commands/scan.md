Scan the entire watchlist. For each stock in data/watchlist.json:

## Step 1: Technical Data
For each stock, fetch price/volume and compute indicators (RSI, MACD, Bollinger Bands).
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
