Portfolio management. Argument: $ARGUMENTS

If no argument or "status":
- Run `python agents/portfolio_agent.py status` to show current portfolio
- Run `python analysis/risk_manager.py report` to show risk dashboard
- Run `python analysis/trade_journal.py status` to show open trades
- Run `python analysis/trade_journal.py winrate` to show performance stats
- Display cash balance, holdings, P&L, recent transactions, risk, and journal

If argument contains a transaction (e.g., "ซื้อ PTT 1000", "buy PTT 5000", "sell ADVANC 3000"):
- Parse the transaction: action (ซื้อ/buy → BUY, ขาย/sell → SELL), symbol, amount
- Fetch current price: `python agents/data_collector.py --symbol SYMBOL`
- For BUY: Run `python analysis/risk_manager.py check-buy --symbol SYMBOL --amount AMOUNT` to validate
- Record the transaction: `python agents/portfolio_agent.py buy/sell --symbol SYMBOL --amount AMOUNT --price PRICE`
- Transaction auto-records in trade journal
- Confirm the transaction and show updated portfolio

Display portfolio in this format:

**สถานะพอร์ต**
- เงินสด: ฿xxx
- มูลค่าหุ้น: ฿xxx
- มูลค่ารวม: ฿xxx
- กำไร/ขาดทุน: ฿xxx
- Deployment: x%

**หุ้นที่ถืออยู่**
| หุ้น | จำนวน | ต้นทุน | ราคาปัจจุบัน | P&L |
|------|-------|--------|-------------|-----|

**Risk Summary**
- Portfolio Heat: x% (LOW/MEDIUM/HIGH)
- Stop-Loss Alerts: list any triggered
- Sector Concentration: OK or warnings

**Trade Journal**
- Open trades: X
- Win Rate: x% (Y wins / Z trades)
- Total P&L (closed): ฿xxx

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
