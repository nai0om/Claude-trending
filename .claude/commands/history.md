Show alert history for the last 7 days.

1. Check `data/alerts.db` for recent alert records
2. If the database doesn't exist yet, inform the user that no alerts have been generated

Display:
- **Recent Alerts**: Date, symbol, alert type (BUY/SELL/WATCH), composite score, confidence
- **Alert Summary**: Count of BUY vs SELL vs WATCH alerts
- **Performance**: If we can track, show how alerts performed after being sent (did the stock move in the predicted direction?)

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
