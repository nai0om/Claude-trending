Generate today's daily action plan.

This runs the FULL analysis pipeline on all watchlist stocks — not just technicals.

1. Run `python analysis/risk_manager.py snapshot` — record daily portfolio snapshot
2. Run `python agents/action_plan_agent.py --budget 100000` — full pipeline per stock:
   - Technical (RSI, MACD, Bollinger, volume)
   - Sentiment (social media, webboards via Search Center API)
   - Fundamental (SEC API financial ratios, F-Score — quick mode)
   - News (articles + webboard discussions)
   - Composite score (weighted combination of all sources)
   - Risk checks (position limits, deployment cap, daily loss halt)
3. Run `python analysis/risk_manager.py report` — portfolio-wide risk dashboard

Analyze all results and provide:

**แผนการลงทุนวันนี้ (Daily Action Plan)**

| หุ้น | Sector | สัญญาณ | คะแนน | จำนวนเงิน | เหตุผล |
|------|--------|--------|-------|-----------|--------|
| ... | ... | BUY/SELL/HOLD | score | ฿xxx | summary of all signals |

For each stock, the reasoning should include data from ALL available sources (T=technical, S=sentiment, F=fundamental, N=news). Flag which sources were unavailable.

**Score Breakdown** (for any BUY or SELL signals):
Show the component scores: Technical, Sentiment, Fundamental, News, Volume, Fund Flow

**สรุป**:
- จำนวนซื้อ: X ตัว (฿xxx)
- จำนวนขาย: X ตัว
- จำนวนถือ: X ตัว
- Data sources used: T/S/F/N per stock

**Risk Alerts**:
- List any risk warnings (daily loss halt, position limits, sector concentration, stop-losses)
- If no warnings: "All risk checks passed"

**BUY Signal Challenges** (for any BUY recommendations):
For each BUY signal, briefly note 1-2 counter-arguments or blind spots. This is a mini-challenge — if the user wants a full devil's advocate, they should run `/challenge SYMBOL`.

**ความเห็น**: Your analysis of today's market conditions and why you recommend these actions. Note any data gaps that reduce confidence.

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
