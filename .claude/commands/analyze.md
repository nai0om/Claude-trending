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

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
