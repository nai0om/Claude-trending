Portfolio management. Argument: $ARGUMENTS

If no argument or "status":
- Run `python agents/portfolio_agent.py status` to show current portfolio
- Display cash balance, holdings, P&L, recent transactions

If argument contains a transaction (e.g., "ซื้อ PTT 1000", "buy PTT 5000", "sell ADVANC 3000"):
- Parse the transaction: action (ซื้อ/buy → BUY, ขาย/sell → SELL), symbol, amount
- Fetch current price: `python agents/data_collector.py --symbol SYMBOL`
- Record the transaction: `python agents/portfolio_agent.py buy/sell --symbol SYMBOL --amount AMOUNT --price PRICE`
- Confirm the transaction and show updated portfolio

Display portfolio in this format:

**💼 สถานะพอร์ต**
- 💰 เงินสด: ฿xxx
- 📈 มูลค่าหุ้น: ฿xxx
- 🏦 มูลค่ารวม: ฿xxx
- 📊 กำไร/ขาดทุน: ฿xxx

**หุ้นที่ถืออยู่**
| หุ้น | จำนวน | ต้นทุน | ราคาปัจจุบัน | P&L |
|------|-------|--------|-------------|-----|

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
