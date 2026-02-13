💼 **สถานะพอร์ต**
━━━━━━━━━━━━━━━
📅 ณ วันที่: {{date}}

💰 **เงินสด**: {{cash_balance}} บาท
📈 **มูลค่าหุ้น**: {{total_market_value}} บาท
🏦 **มูลค่ารวม**: {{total_portfolio_value}} บาท
📊 **กำไร/ขาดทุน**: {{total_pnl}} บาท

**หุ้นที่ถืออยู่**
{{#holdings}}
- **{{symbol}}**: {{shares}} หุ้น @ {{avg_cost}} บาท
  ราคาปัจจุบัน: {{current_price}} | P&L: {{pnl}} ({{pnl_pct}}%)
{{/holdings}}

**ธุรกรรมล่าสุด**
{{#transactions}}
- {{timestamp}}: {{action}} {{symbol}} {{shares}} หุ้น @ {{price}} ({{amount}} บาท)
{{/transactions}}

⚠️ ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
