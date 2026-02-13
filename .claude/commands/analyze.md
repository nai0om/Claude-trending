Deep analysis for a single stock: $ARGUMENTS

Run these commands and analyze all the data:

1. `python agents/data_collector.py --symbol $ARGUMENTS` — fetch 6-month price/volume history
2. `python agents/technical_agent.py --symbol $ARGUMENTS` — technical indicators (RSI, MACD, Bollinger Bands, support/resistance)
3. `python scrapers/pantip_scraper.py --symbol $ARGUMENTS` — Pantip sentiment data
4. `python scrapers/news_scraper.py --symbol $ARGUMENTS` — latest news

Analyze all the collected data and provide:
- **Technical Analysis**: Interpret RSI, MACD, Bollinger Bands, support/resistance levels
- **Price Action**: Recent trend, key levels, volume patterns
- **Sentiment**: Social media and news sentiment (if data available)
- **Signals**: BUY/SELL/HOLD signals with reasoning
- **Risk Factors**: What could go wrong
- **Confidence Level**: Low/Medium/High based on data quality

## Data Persistence (REQUIRED)

After analysis, you MUST save results to `data/stocks/{SYMBOL}.json`:
- READ the existing file first to preserve historical data
- APPEND a new entry to the `scans` array with all indicator data
- Add any notable findings to the `notes` array with format:
  ```json
  { "date": "YYYY-MM-DD", "type": "analyze", "content": "Key findings summary" }
  ```
- If the file does not exist, create it with the full structure (see /scan for schema)

IMPORTANT: Always read existing stock files before writing to preserve historical data. Never overwrite — always append.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
