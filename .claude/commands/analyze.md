Deep analysis for a single stock: $ARGUMENTS

Run these commands and analyze all the data:

## Step 1: Technical Data
1. `python agents/data_collector.py --symbol $ARGUMENTS` — fetch 6-month price/volume history
2. `python agents/technical_agent.py --symbol $ARGUMENTS` — technical indicators (RSI, MACD, Bollinger Bands, support/resistance)

## Step 2: Social Sentiment (Search Center API)
3. `python agents/sentiment_agent.py --symbol $ARGUMENTS` — full sentiment analysis (mentions, sentiment score, channel breakdown, top posts)
4. `python scrapers/search_center_client.py --action timeline --symbol $ARGUMENTS --days 14` — 14-day mention trend to detect spikes
5. `python scrapers/search_center_client.py --action hashtags --symbol $ARGUMENTS --days 7` — related trending hashtags

## Step 3: News
6. `python agents/news_agent.py --symbol $ARGUMENTS` — news articles + webboard (Pantip) discussions

Analyze all the collected data and provide:
- **Technical Analysis**: Interpret RSI, MACD, Bollinger Bands, support/resistance levels
- **Price Action**: Recent trend, key levels, volume patterns
- **Sentiment**: Social media sentiment score, mention volume, channel breakdown, top posts with URLs
- **News**: Recent news headlines and their sentiment
- **Signals**: BUY/SELL/HOLD signals with reasoning (combining technical + sentiment)
- **Risk Factors**: What could go wrong (include sentiment divergence from price if any)
- **Confidence Level**: Low/Medium/High based on data quality and sample size

## Data Persistence (REQUIRED)

After analysis, you MUST save results to `data/stocks/{SYMBOL}.json`:
- READ the existing file first to preserve historical data
- APPEND a new entry to the `scans` array with all indicator data + sentiment data
- Add any notable findings to the `notes` array with format:
  ```json
  { "date": "YYYY-MM-DD", "type": "analyze", "content": "Key findings summary" }
  ```
- If the file does not exist, create it with the full structure (see /scan for schema)

IMPORTANT: Always read existing stock files before writing to preserve historical data. Never overwrite — always append.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
