Scan the entire watchlist. For each stock in data/watchlist.json:

1. Run `python agents/data_collector.py --symbol SYMBOL` to fetch latest price/volume data
2. Run `python agents/technical_agent.py --symbol SYMBOL` to get RSI, MACD, Bollinger Bands
3. Review all results and provide a summary table with:
   - Symbol | Price | RSI | MACD Signal | Volume vs Avg | Overall Signal
4. Flag any stocks with unusual signals (RSI < 30 or > 70, volume > 2x average)
5. Provide your analysis of the overall market sentiment based on the data

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
