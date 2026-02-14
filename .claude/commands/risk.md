Risk dashboard for current portfolio.

Run all risk checks:

1. Record today's snapshot: `python analysis/risk_manager.py snapshot`
2. Full risk report: `python analysis/risk_manager.py report`
3. Stop-loss check: `python analysis/risk_manager.py stop-losses`

Analyze all results and display:

**Risk Dashboard**

| Metric | Value | Status |
|--------|-------|--------|
| Portfolio Heat | x.x% | LOW/MEDIUM/HIGH |
| Deployment % | x.x% | (cap 50%) |
| Daily P&L | x.x% | OK / HALT |
| Sector Concentration | OK / WARNING | |

**Stop-Loss Alerts**
| Symbol | P&L % | Distance to Stop | Status |
|--------|-------|-------------------|--------|
| ... | ... | ... | OK / TRIGGERED |

**Sector Breakdown**
| Sector | Value | Weight |
|--------|-------|--------|
| ... | ฿xxx | x% |

**Warnings**: List all active warnings. If no warnings, show "All clear."

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
