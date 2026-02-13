Scan the entire watchlist. For each stock in data/watchlist.json:

1. Run `python agents/data_collector.py --symbol SYMBOL` to fetch latest price/volume data
2. Run `python agents/technical_agent.py --symbol SYMBOL` to get RSI, MACD, Bollinger Bands
3. Review all results and provide a summary table with:
   - Symbol | Price | RSI | MACD Signal | Volume vs Avg | Overall Signal
4. Flag any stocks with unusual signals (RSI < 30 or > 70, volume > 2x average)
5. Provide your analysis of the overall market sentiment based on the data

## Data Persistence (REQUIRED)

After collecting all data, you MUST save results to files:

### Per-stock files: `data/stocks/{SYMBOL}.json`
- If the file already exists, READ it first, then APPEND a new entry to the `scans` array
- If the file does not exist, create it with the structure below
- Each scan entry includes: date, price, indicators (RSI, MACD, BB), volume stats, support/resistance, flags, signal

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
- Include: market_sentiment, stocks_scanned, overbought/oversold counts, flagged stocks
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
  "summary": [ { "symbol": "", "close": 0, "rsi": 0, "macd_signal": "", "vol_ratio": 0, "signal": "" } ],
  "flagged": { "overbought": [], "oversold": [], "high_volume": [], "price_breakout": [] }
}
```

IMPORTANT: Always read existing stock files before writing to preserve historical scan data. Never overwrite — always append.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
