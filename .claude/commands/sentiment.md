Market-wide sentiment overview.

Use the Search Center API (http://localhost:4344) to fetch real social media data.

1. Run `python scrapers/search_center_client.py --action compare --symbols PTT ADVANC AOT CPALL GULF KBANK SCB SCC BDMS DELTA --days 7` — compare all watchlist stocks
2. For the top 3 most-mentioned stocks, run `python agents/sentiment_agent.py --symbol SYMBOL` to get detailed sentiment + top posts
3. Run `python scrapers/search_center_client.py --action hashtags --symbol หุ้น --days 7` — get trending hashtags

Analyze all the data and provide:
- **Overall Market Mood**: Bullish / Bearish / Neutral based on social data
- **Most Discussed Stocks**: Which stocks are getting the most mentions and engagement
- **Sentiment by Stock**: Table with positive/neutral/negative % for each stock
- **Trending Topics**: Top hashtags and themes investors are discussing
- **Notable Posts**: High-engagement posts worth highlighting (with URLs)
- **Contrarian Signals**: Any stocks where sentiment seems extreme (potential reversal)

## Data Persistence (REQUIRED)

Save sentiment results to each stock's file in `data/stocks/{SYMBOL}.json`:
- READ existing file first, then add/update a `sentiment` key:
  ```json
  {
    "sentiment": [
      {
        "date": "YYYY-MM-DD",
        "score": 0.0,
        "label": "Bullish/Bearish/Neutral",
        "total_mentions": 0,
        "positive": 0,
        "neutral": 0,
        "negative": 0,
        "confidence": "Low/Medium/High"
      }
    ]
  }
  ```

IMPORTANT: Always read existing stock files before writing to preserve historical data. Never overwrite — always append.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
