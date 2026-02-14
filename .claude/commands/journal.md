Trade journal management. Argument: $ARGUMENTS

If no argument or "status":
- Run `python analysis/trade_journal.py status` to show open trades
- Run `python analysis/trade_journal.py winrate` to show performance stats
- Run `python analysis/trade_journal.py strategies` to show strategy breakdown
- Display all results

If argument starts with "close" (e.g., "close KBANK 250"):
- Parse: symbol and exit price from the argument
- Run `python analysis/trade_journal.py close --symbol SYMBOL --price PRICE`
- Ask user for outcome and lessons learned (optional)
- Show updated win rate after closing

If argument starts with "history":
- Run `python analysis/trade_journal.py history`
- Display trade history

Display open trades in this format:

**Trade Journal**

**Open Trades**
| Symbol | Action | Entry | Shares | Amount | Strategy | Reasoning |
|--------|--------|-------|--------|--------|----------|-----------|
| ... | BUY/SELL | ฿xxx | xxx | ฿xxx | ... | ... |

**Performance (Closed Trades)**
| Metric | Value |
|--------|-------|
| Total Trades | x |
| Win Rate | x% |
| Avg Win | ฿xxx (x%) |
| Avg Loss | ฿xxx (x%) |
| Profit Factor | x.x |
| Kelly Fraction | x% |
| Total P&L | ฿xxx |

**Strategy Breakdown**
| Strategy | Trades | Win Rate | Total P&L |
|----------|--------|----------|-----------|
| ... | x | x% | ฿xxx |

Remember: ข้อมูลประกอบการตัดสินใจเท่านั้น ไม่ใช่คำแนะนำในการลงทุน
