"""Trade Journal — records trades with reasoning, tracks outcomes, win rate, strategy performance."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"
SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def _load_settings() -> dict:
    with open(SETTINGS_PATH) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("trade_journal", {
        "default_strategy": "composite",
        "auto_record": True,
    })


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_journal_db():
    """Create trade_journal table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS trade_journal (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
            entry_price REAL,
            entry_date TEXT,
            exit_price REAL,
            exit_date TEXT,
            shares REAL NOT NULL DEFAULT 0,
            amount REAL NOT NULL DEFAULT 0,
            reasoning TEXT,
            strategy TEXT DEFAULT 'composite',
            signals_at_entry TEXT,
            outcome TEXT,
            lessons TEXT,
            pnl REAL DEFAULT 0,
            pnl_pct REAL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'CLOSED', 'STOPPED_OUT')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def open_trade(
    symbol: str,
    action: str,
    price: float,
    shares: float,
    amount: float,
    reasoning: str = "",
    strategy: str = "",
    signals_at_entry: Optional[dict] = None,
) -> dict:
    """Record a new trade entry in the journal.

    Args:
        symbol: Stock symbol
        action: 'BUY' or 'SELL'
        price: Entry price
        shares: Number of shares
        amount: Total amount in THB
        reasoning: Why this trade was made
        strategy: Strategy label (e.g., 'composite', 'momentum', 'value')
        signals_at_entry: Dict of indicator values at entry time

    Returns:
        Dict with the new journal entry.
    """
    init_journal_db()
    settings = _load_settings()
    now = datetime.now().isoformat()

    if not strategy:
        strategy = settings.get("default_strategy", "composite")

    signals_json = json.dumps(signals_at_entry, default=str) if signals_at_entry else "{}"

    conn = _get_conn()
    cursor = conn.execute("""
        INSERT INTO trade_journal
            (symbol, action, entry_price, entry_date, shares, amount, reasoning, strategy, signals_at_entry, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', ?, ?)
    """, (symbol, action, price, now, shares, amount, reasoning, strategy, signals_json, now, now))

    trade_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {
        "id": trade_id,
        "symbol": symbol,
        "action": action,
        "entry_price": price,
        "shares": shares,
        "amount": amount,
        "strategy": strategy,
        "status": "OPEN",
    }


def close_trade(
    trade_id: Optional[int] = None,
    symbol: Optional[str] = None,
    exit_price: float = 0,
    outcome: str = "",
    lessons: str = "",
    status: str = "CLOSED",
) -> dict:
    """Close an open trade and record the outcome.

    Args:
        trade_id: Journal entry ID to close (preferred)
        symbol: Symbol to close most recent open trade for (fallback)
        exit_price: Exit price per share
        outcome: Brief outcome description
        lessons: Lessons learned
        status: 'CLOSED' or 'STOPPED_OUT'
    """
    init_journal_db()
    conn = _get_conn()
    now = datetime.now().isoformat()

    if trade_id:
        trade = conn.execute("SELECT * FROM trade_journal WHERE id = ? AND status = 'OPEN'", (trade_id,)).fetchone()
    elif symbol:
        trade = conn.execute(
            "SELECT * FROM trade_journal WHERE symbol = ? AND status = 'OPEN' ORDER BY created_at DESC LIMIT 1",
            (symbol,),
        ).fetchone()
    else:
        conn.close()
        return {"error": "Provide trade_id or symbol"}

    if not trade:
        conn.close()
        return {"error": "No open trade found"}

    # Calculate P&L
    entry_price = trade["entry_price"]
    shares = trade["shares"]
    action = trade["action"]

    if action == "BUY":
        pnl = (exit_price - entry_price) * shares
    else:  # SELL (short)
        pnl = (entry_price - exit_price) * shares

    pnl_pct = pnl / (entry_price * shares) if entry_price * shares > 0 else 0

    conn.execute("""
        UPDATE trade_journal
        SET exit_price = ?, exit_date = ?, pnl = ?, pnl_pct = ?,
            outcome = ?, lessons = ?, status = ?, updated_at = ?
        WHERE id = ?
    """, (exit_price, now, round(pnl, 2), round(pnl_pct, 4), outcome, lessons, status, now, trade["id"]))

    conn.commit()
    conn.close()

    return {
        "id": trade["id"],
        "symbol": trade["symbol"],
        "action": action,
        "entry_price": entry_price,
        "exit_price": exit_price,
        "shares": shares,
        "pnl": round(pnl, 2),
        "pnl_pct": round(pnl_pct, 4),
        "status": status,
        "outcome": outcome,
    }


def get_open_trades() -> list[dict]:
    """Get all currently open trades."""
    init_journal_db()
    conn = _get_conn()
    trades = conn.execute(
        "SELECT * FROM trade_journal WHERE status = 'OPEN' ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(t) for t in trades]


def get_trade_history(limit: int = 50) -> list[dict]:
    """Get closed trade history."""
    init_journal_db()
    conn = _get_conn()
    trades = conn.execute(
        "SELECT * FROM trade_journal WHERE status != 'OPEN' ORDER BY updated_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(t) for t in trades]


def get_win_rate() -> dict:
    """Calculate win rate, avg win/loss, profit factor, and Kelly fraction.

    Returns:
        Dict with performance statistics.
    """
    init_journal_db()
    conn = _get_conn()
    closed = conn.execute(
        "SELECT * FROM trade_journal WHERE status IN ('CLOSED', 'STOPPED_OUT')"
    ).fetchall()
    conn.close()

    if not closed:
        return {
            "total_trades": 0,
            "message": "No closed trades yet",
        }

    wins = [t for t in closed if t["pnl"] > 0]
    losses = [t for t in closed if t["pnl"] <= 0]
    stopped = [t for t in closed if t["status"] == "STOPPED_OUT"]

    total = len(closed)
    win_count = len(wins)
    loss_count = len(losses)

    win_rate = win_count / total if total > 0 else 0
    avg_win = sum(t["pnl"] for t in wins) / win_count if win_count > 0 else 0
    avg_loss = abs(sum(t["pnl"] for t in losses) / loss_count) if loss_count > 0 else 0
    total_pnl = sum(t["pnl"] for t in closed)

    # Profit factor = gross profit / gross loss
    gross_profit = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float("inf")

    # Kelly criterion
    from analysis.position_sizing import kelly_criterion
    kelly = kelly_criterion(win_rate, avg_win, avg_loss) if avg_loss > 0 else 0

    # Avg win % and avg loss %
    avg_win_pct = sum(t["pnl_pct"] for t in wins) / win_count if win_count > 0 else 0
    avg_loss_pct = sum(t["pnl_pct"] for t in losses) / loss_count if loss_count > 0 else 0

    return {
        "total_trades": total,
        "wins": win_count,
        "losses": loss_count,
        "stopped_out": len(stopped),
        "win_rate": round(win_rate, 4),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "avg_win_pct": round(avg_win_pct, 4),
        "avg_loss_pct": round(avg_loss_pct, 4),
        "total_pnl": round(total_pnl, 2),
        "profit_factor": round(profit_factor, 2),
        "kelly_fraction": round(kelly, 4),
        "kelly_pct": f"{kelly:.1%}",
    }


def get_strategy_performance() -> dict:
    """Breakdown performance by strategy type."""
    init_journal_db()
    conn = _get_conn()
    closed = conn.execute(
        "SELECT * FROM trade_journal WHERE status IN ('CLOSED', 'STOPPED_OUT')"
    ).fetchall()
    conn.close()

    if not closed:
        return {"strategies": [], "message": "No closed trades yet"}

    by_strategy = {}
    for t in closed:
        strat = t["strategy"] or "unknown"
        if strat not in by_strategy:
            by_strategy[strat] = {"wins": 0, "losses": 0, "total_pnl": 0, "trades": 0}
        by_strategy[strat]["trades"] += 1
        by_strategy[strat]["total_pnl"] += t["pnl"]
        if t["pnl"] > 0:
            by_strategy[strat]["wins"] += 1
        else:
            by_strategy[strat]["losses"] += 1

    strategies = []
    for name, data in sorted(by_strategy.items(), key=lambda x: -x[1]["total_pnl"]):
        win_rate = data["wins"] / data["trades"] if data["trades"] > 0 else 0
        strategies.append({
            "strategy": name,
            "trades": data["trades"],
            "wins": data["wins"],
            "losses": data["losses"],
            "win_rate": round(win_rate, 4),
            "total_pnl": round(data["total_pnl"], 2),
        })

    return {"strategies": strategies}


def main():
    parser = argparse.ArgumentParser(description="Trade journal")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show open trades")
    sub.add_parser("history", help="Show trade history")
    sub.add_parser("winrate", help="Show win rate statistics")
    sub.add_parser("strategies", help="Show strategy performance")

    open_parser = sub.add_parser("open", help="Open a new trade")
    open_parser.add_argument("--symbol", required=True)
    open_parser.add_argument("--action", required=True, choices=["BUY", "SELL"])
    open_parser.add_argument("--price", type=float, required=True)
    open_parser.add_argument("--shares", type=float, required=True)
    open_parser.add_argument("--amount", type=float, required=True)
    open_parser.add_argument("--reasoning", default="")
    open_parser.add_argument("--strategy", default="")

    close_parser = sub.add_parser("close", help="Close a trade")
    close_parser.add_argument("--symbol", required=True)
    close_parser.add_argument("--price", type=float, required=True)
    close_parser.add_argument("--outcome", default="")
    close_parser.add_argument("--lessons", default="")
    close_parser.add_argument("--stopped-out", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.command == "status":
        result = get_open_trades()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "history":
        result = get_trade_history()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "winrate":
        result = get_win_rate()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "strategies":
        result = get_strategy_performance()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "open":
        result = open_trade(
            symbol=args.symbol,
            action=args.action,
            price=args.price,
            shares=args.shares,
            amount=args.amount,
            reasoning=args.reasoning,
            strategy=args.strategy,
        )
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "close":
        status = "STOPPED_OUT" if args.stopped_out else "CLOSED"
        result = close_trade(
            symbol=args.symbol,
            exit_price=args.price,
            outcome=args.outcome,
            lessons=args.lessons,
            status=status,
        )
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
