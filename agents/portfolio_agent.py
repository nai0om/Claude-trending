"""Portfolio Agent — tracks cash balance, holdings, P&L, and transaction history."""

import argparse
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"


def init_db():
    """Initialize portfolio database tables."""
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            cash_balance REAL NOT NULL DEFAULT 100000,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS holdings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            shares REAL NOT NULL DEFAULT 0,
            avg_cost REAL NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            UNIQUE(symbol)
        );

        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL CHECK(action IN ('BUY', 'SELL')),
            shares REAL NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            timestamp TEXT NOT NULL
        );

        INSERT OR IGNORE INTO portfolio (id, cash_balance, updated_at)
        VALUES (1, 100000, datetime('now'));
    """)
    conn.commit()
    conn.close()


def get_portfolio_status() -> dict:
    """Get current portfolio status including holdings and P&L."""
    init_db()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    portfolio = conn.execute("SELECT * FROM portfolio WHERE id = 1").fetchone()
    holdings = conn.execute("SELECT * FROM holdings WHERE shares > 0").fetchall()
    recent_txns = conn.execute(
        "SELECT * FROM transactions ORDER BY timestamp DESC LIMIT 20"
    ).fetchall()
    conn.close()

    holdings_list = []
    total_market_value = 0
    total_cost = 0

    for h in holdings:
        # TODO: Fetch current market price
        current_price = h["avg_cost"]  # placeholder
        market_value = h["shares"] * current_price
        cost_basis = h["shares"] * h["avg_cost"]
        pnl = market_value - cost_basis

        holdings_list.append({
            "symbol": h["symbol"],
            "shares": h["shares"],
            "avg_cost": h["avg_cost"],
            "current_price": current_price,
            "market_value": round(market_value, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round((pnl / cost_basis * 100) if cost_basis > 0 else 0, 2),
        })
        total_market_value += market_value
        total_cost += cost_basis

    cash = portfolio["cash_balance"]
    total_value = cash + total_market_value

    return {
        "as_of": datetime.now().isoformat(),
        "cash_balance": round(cash, 2),
        "total_market_value": round(total_market_value, 2),
        "total_portfolio_value": round(total_value, 2),
        "total_pnl": round(total_market_value - total_cost, 2),
        "holdings": holdings_list,
        "recent_transactions": [dict(t) for t in recent_txns],
    }


def record_transaction(symbol: str, action: str, amount_thb: float, price: float) -> dict:
    """Record a BUY or SELL transaction.

    Args:
        symbol: Stock symbol (e.g., 'PTT')
        action: 'BUY' or 'SELL'
        amount_thb: Amount in THB
        price: Price per share
    """
    init_db()
    shares = amount_thb / price if price > 0 else 0
    conn = sqlite3.connect(DB_PATH)
    now = datetime.now().isoformat()

    if action == "BUY":
        # Deduct cash
        conn.execute(
            "UPDATE portfolio SET cash_balance = cash_balance - ?, updated_at = ? WHERE id = 1",
            (amount_thb, now),
        )
        # Upsert holding
        existing = conn.execute(
            "SELECT shares, avg_cost FROM holdings WHERE symbol = ?", (symbol,)
        ).fetchone()

        if existing:
            old_shares, old_cost = existing
            new_shares = old_shares + shares
            new_avg_cost = ((old_shares * old_cost) + amount_thb) / new_shares if new_shares > 0 else 0
            conn.execute(
                "UPDATE holdings SET shares = ?, avg_cost = ?, updated_at = ? WHERE symbol = ?",
                (new_shares, new_avg_cost, now, symbol),
            )
        else:
            conn.execute(
                "INSERT INTO holdings (symbol, shares, avg_cost, updated_at) VALUES (?, ?, ?, ?)",
                (symbol, shares, price, now),
            )
    elif action == "SELL":
        # Add cash
        conn.execute(
            "UPDATE portfolio SET cash_balance = cash_balance + ?, updated_at = ? WHERE id = 1",
            (amount_thb, now),
        )
        # Reduce holding
        conn.execute(
            "UPDATE holdings SET shares = shares - ?, updated_at = ? WHERE symbol = ?",
            (shares, now, symbol),
        )

    # Record transaction
    conn.execute(
        "INSERT INTO transactions (symbol, action, shares, price, amount, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
        (symbol, action, shares, price, amount_thb, now),
    )

    conn.commit()
    conn.close()

    return {
        "symbol": symbol,
        "action": action,
        "shares": round(shares, 4),
        "price": price,
        "amount": amount_thb,
        "timestamp": now,
    }


def main():
    parser = argparse.ArgumentParser(description="Portfolio tracker")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="Show portfolio status")

    buy_parser = sub.add_parser("buy", help="Record a buy transaction")
    buy_parser.add_argument("--symbol", required=True)
    buy_parser.add_argument("--amount", type=float, required=True, help="Amount in THB")
    buy_parser.add_argument("--price", type=float, required=True, help="Price per share")

    sell_parser = sub.add_parser("sell", help="Record a sell transaction")
    sell_parser.add_argument("--symbol", required=True)
    sell_parser.add_argument("--amount", type=float, required=True, help="Amount in THB")
    sell_parser.add_argument("--price", type=float, required=True, help="Price per share")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.command == "status":
        result = get_portfolio_status()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command in ("buy", "sell"):
        action = args.command.upper()
        result = record_transaction(args.symbol, action, args.amount, args.price)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
