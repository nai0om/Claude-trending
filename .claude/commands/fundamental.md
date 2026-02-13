Deep fundamental analysis for: $ARGUMENTS

Run these commands and analyze the financial data:

1. `python scrapers/sec_api_client.py --symbol $ARGUMENTS --periods 8` — fetch 8 quarters of financial statements
2. `python analysis/financial_health.py --symbol $ARGUMENTS` — compute Piotroski F-Score
3. `python analysis/fundamental.py --symbol $ARGUMENTS` — compute financial ratios

Analyze all the financial data and provide:
- **Financial Overview**: Revenue trend, net income trend, margins
- **Profitability**: ROE, ROA, net margin — and how they trend over quarters
- **Financial Health**: D/E ratio, current ratio, cash flow quality
- **Piotroski F-Score**: Score breakdown (0-9) and interpretation
- **Growth**: QoQ and YoY profit growth
- **Grade**: Overall grade A-F with reasoning
- **Valuation**: Is the stock cheap or expensive relative to fundamentals?
- **Red Flags**: Any concerning trends (rising debt, declining margins, etc.)

Compare at least 3 quarters of data to identify trends.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
