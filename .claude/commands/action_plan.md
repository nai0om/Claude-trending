Generate today's daily action plan.

Run full analysis on all watchlist stocks and create an action plan:

1. For each stock in data/watchlist.json:
   - Run `python agents/data_collector.py --symbol SYMBOL` — latest price/volume
   - Run `python agents/technical_agent.py --symbol SYMBOL` — technical signals
2. Run `python agents/action_plan_agent.py --budget 100000` — generate action plan
3. Run `python analysis/risk_manager.py report` — risk checks on current portfolio
4. Run `python analysis/risk_manager.py snapshot` — record daily snapshot

Analyze all results and provide:

**แผนการลงทุนวันนี้ (Daily Action Plan)**

| หุ้น | Sector | สัญญาณ | คะแนน | จำนวนเงิน | เหตุผล |
|------|--------|--------|-------|-----------|--------|
| ... | ... | BUY/SELL/HOLD | score | ฿xxx | ... |

**สรุป**:
- จำนวนซื้อ: X ตัว (฿xxx)
- จำนวนขาย: X ตัว
- จำนวนถือ: X ตัว

**Risk Alerts**:
- List any risk warnings from the action plan (daily loss halt, position limits, sector concentration)
- If no warnings: "All risk checks passed"

**ความเห็น**: Your analysis of today's market conditions and why you recommend these actions.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
