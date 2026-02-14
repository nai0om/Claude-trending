"""Risk Manager — portfolio risk checks: position limits, stop-losses, daily loss halt, heat, sector concentration."""

from __future__ import annotations

import argparse
import json
import logging
import sqlite3
from datetime import date, datetime
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "portfolio.db"
CONFIG_PATH = Path(__file__).parent.parent / "config" / "thresholds.yaml"
WATCHLIST_PATH = Path(__file__).parent.parent / "data" / "watchlist.json"


def _load_config() -> dict:
    """Load risk_management config from thresholds.yaml."""
    with open(CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("risk_management", {
        "max_position_pct": 0.15,
        "total_deployment_cap": 0.50,
        "stop_loss_pct": -0.15,
        "daily_loss_halt_pct": -0.05,
        "max_sector_pct": 0.40,
        "portfolio_heat_high": 0.15,
        "portfolio_heat_medium": 0.08,
    })


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _init_snapshots():
    """Create daily_snapshots table if it doesn't exist."""
    conn = _get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            total_value REAL NOT NULL,
            cash_balance REAL NOT NULL,
            market_value REAL NOT NULL,
            daily_pnl REAL DEFAULT 0,
            daily_pnl_pct REAL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(snapshot_date)
        )
    """)
    conn.commit()
    conn.close()


def _get_portfolio_data() -> dict:
    """Get current portfolio holdings and cash."""
    conn = _get_conn()
    portfolio = conn.execute("SELECT * FROM portfolio WHERE id = 1").fetchone()
    holdings = conn.execute("SELECT * FROM holdings WHERE shares > 0").fetchall()
    conn.close()

    if not portfolio:
        return {"cash": 0, "holdings": []}

    return {
        "cash": portfolio["cash_balance"],
        "holdings": [dict(h) for h in holdings],
    }


def _get_current_price(symbol: str) -> float:
    """Fetch current price via yfinance. Returns avg_cost as fallback."""
    try:
        import yfinance as yf
        ticker = yf.Ticker(f"{symbol}.BK")
        hist = ticker.history(period="5d")
        if not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception as e:
        logger.warning("Could not fetch price for %s: %s", symbol, e)
    return 0.0


def _get_volatility(symbol: str, window: int = 20) -> float:
    """Compute 20-day annualized volatility for a symbol."""
    try:
        import yfinance as yf
        import numpy as np
        ticker = yf.Ticker(f"{symbol}.BK")
        hist = ticker.history(period="2mo")
        if len(hist) >= window:
            returns = hist["Close"].pct_change().dropna().tail(window)
            return float(np.std(returns) * np.sqrt(252))
    except Exception as e:
        logger.warning("Could not compute volatility for %s: %s", symbol, e)
    return 0.0


def _get_sector_for_symbol(symbol: str) -> str:
    """Look up sector from watchlist.json."""
    try:
        with open(WATCHLIST_PATH) as f:
            watchlist = json.load(f)
        for stock in watchlist.get("watchlist", []):
            if stock["symbol"] == symbol:
                return stock.get("sector", "Unknown")
    except Exception:
        pass
    return "Unknown"


def check_position_limits(symbol: str, amount: float) -> dict:
    """Check if a proposed BUY violates position limits.

    Returns:
        Dict with 'allowed', 'max_allowed', and 'warnings'.
    """
    cfg = _load_config()
    data = _get_portfolio_data()
    max_pct = cfg["max_position_pct"]
    deploy_cap = cfg["total_deployment_cap"]

    total_market = 0
    existing_value = 0

    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        value = h["shares"] * price
        total_market += value
        if h["symbol"] == symbol:
            existing_value = value

    total_value = data["cash"] + total_market
    warnings = []

    # Check max position %
    new_position_value = existing_value + amount
    position_pct = new_position_value / total_value if total_value > 0 else 0
    max_allowed_position = total_value * max_pct - existing_value

    if position_pct > max_pct:
        warnings.append(
            f"Position limit: {symbol} would be {position_pct:.1%} of portfolio "
            f"(max {max_pct:.0%}). Max additional: {max(0, max_allowed_position):,.0f} THB"
        )

    # Check total deployment cap
    new_deployed = (total_market + amount) / total_value if total_value > 0 else 0
    max_deploy_amount = total_value * deploy_cap - total_market

    if new_deployed > deploy_cap:
        warnings.append(
            f"Deployment cap: portfolio would be {new_deployed:.1%} deployed "
            f"(max {deploy_cap:.0%}). Max additional: {max(0, max_deploy_amount):,.0f} THB"
        )

    allowed_amount = min(
        max(0, max_allowed_position),
        max(0, max_deploy_amount),
        amount,
    )

    return {
        "symbol": symbol,
        "requested_amount": amount,
        "allowed": len(warnings) == 0,
        "allowed_amount": round(allowed_amount, 2),
        "position_pct": round(position_pct, 4),
        "deployment_pct": round(new_deployed, 4),
        "warnings": warnings,
    }


def check_stop_losses() -> list[dict]:
    """Check all holdings for stop-loss violations.

    Returns list of holdings that have hit the stop-loss threshold.
    """
    cfg = _load_config()
    stop_pct = cfg["stop_loss_pct"]
    data = _get_portfolio_data()
    alerts = []

    for h in data["holdings"]:
        current = _get_current_price(h["symbol"])
        if current <= 0:
            current = h["avg_cost"]

        pnl_pct = (current - h["avg_cost"]) / h["avg_cost"] if h["avg_cost"] > 0 else 0
        market_value = h["shares"] * current

        entry = {
            "symbol": h["symbol"],
            "shares": h["shares"],
            "avg_cost": h["avg_cost"],
            "current_price": round(current, 2),
            "pnl_pct": round(pnl_pct, 4),
            "market_value": round(market_value, 2),
            "stop_loss_threshold": stop_pct,
        }

        if pnl_pct <= stop_pct:
            entry["triggered"] = True
            entry["message"] = (
                f"STOP-LOSS: {h['symbol']} at {pnl_pct:.1%} "
                f"(threshold {stop_pct:.0%})"
            )
        else:
            entry["triggered"] = False
            distance = pnl_pct - stop_pct
            entry["distance_to_stop"] = round(distance, 4)

        alerts.append(entry)

    return alerts


def check_daily_loss_halt() -> dict:
    """Check if portfolio has dropped enough today to halt all BUY orders.

    Returns dict with 'halt_active' bool and details.
    """
    _init_snapshots()
    cfg = _load_config()
    halt_pct = cfg["daily_loss_halt_pct"]
    data = _get_portfolio_data()

    # Compute current total value
    total_market = 0
    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        total_market += h["shares"] * price
    current_total = data["cash"] + total_market

    # Get yesterday's or most recent snapshot
    conn = _get_conn()
    prev = conn.execute(
        "SELECT total_value FROM daily_snapshots WHERE snapshot_date < ? ORDER BY snapshot_date DESC LIMIT 1",
        (date.today().isoformat(),),
    ).fetchone()
    conn.close()

    if not prev:
        return {
            "halt_active": False,
            "reason": "No previous snapshot — run 'snapshot' first",
            "current_value": round(current_total, 2),
        }

    prev_value = prev["total_value"]
    daily_change = (current_total - prev_value) / prev_value if prev_value > 0 else 0

    halt_active = daily_change <= halt_pct

    return {
        "halt_active": halt_active,
        "previous_value": round(prev_value, 2),
        "current_value": round(current_total, 2),
        "daily_change_pct": round(daily_change, 4),
        "halt_threshold": halt_pct,
        "message": (
            f"HALT ACTIVE: Portfolio down {daily_change:.2%} today (threshold {halt_pct:.0%}). All BUY orders blocked."
            if halt_active
            else f"No halt. Daily change: {daily_change:.2%} (threshold {halt_pct:.0%})"
        ),
    }


def compute_portfolio_heat() -> dict:
    """Compute portfolio heat = sum(weight * 20d volatility) per position.

    High heat means the portfolio is overly exposed to volatile positions.
    """
    cfg = _load_config()
    data = _get_portfolio_data()

    total_market = 0
    position_data = []

    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        value = h["shares"] * price
        total_market += value
        vol = _get_volatility(h["symbol"])
        position_data.append({
            "symbol": h["symbol"],
            "market_value": round(value, 2),
            "volatility_20d": round(vol, 4),
        })

    total_value = data["cash"] + total_market
    total_heat = 0

    for p in position_data:
        weight = p["market_value"] / total_value if total_value > 0 else 0
        heat_contribution = weight * p["volatility_20d"]
        p["weight"] = round(weight, 4)
        p["heat_contribution"] = round(heat_contribution, 4)
        total_heat += heat_contribution

    heat_high = cfg["portfolio_heat_high"]
    heat_med = cfg["portfolio_heat_medium"]

    if total_heat >= heat_high:
        level = "HIGH"
    elif total_heat >= heat_med:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "total_heat": round(total_heat, 4),
        "level": level,
        "thresholds": {"high": heat_high, "medium": heat_med},
        "positions": position_data,
    }


def check_sector_concentration() -> dict:
    """Check sector concentration. Max 40% in any one sector."""
    cfg = _load_config()
    max_sector = cfg["max_sector_pct"]
    data = _get_portfolio_data()

    sector_values = {}
    total_market = 0

    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        value = h["shares"] * price
        total_market += value
        sector = _get_sector_for_symbol(h["symbol"])
        sector_values[sector] = sector_values.get(sector, 0) + value

    total_value = data["cash"] + total_market
    sectors = []
    warnings = []

    for sector, value in sorted(sector_values.items(), key=lambda x: -x[1]):
        pct = value / total_value if total_value > 0 else 0
        entry = {"sector": sector, "value": round(value, 2), "pct": round(pct, 4)}
        sectors.append(entry)
        if pct > max_sector:
            warnings.append(
                f"Sector {sector} at {pct:.1%} (max {max_sector:.0%})"
            )

    return {
        "sectors": sectors,
        "max_sector_pct": max_sector,
        "warnings": warnings,
        "within_limits": len(warnings) == 0,
    }


def check_portfolio_risk() -> dict:
    """Combined risk report — all checks in one call."""
    stop_losses = check_stop_losses()
    daily_halt = check_daily_loss_halt()
    heat = compute_portfolio_heat()
    sectors = check_sector_concentration()
    data = _get_portfolio_data()

    # Compute deployment %
    total_market = 0
    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        total_market += h["shares"] * price
    total_value = data["cash"] + total_market
    deployment_pct = total_market / total_value if total_value > 0 else 0

    triggered_stops = [s for s in stop_losses if s.get("triggered")]

    all_warnings = []
    if triggered_stops:
        all_warnings.extend([s["message"] for s in triggered_stops])
    if daily_halt["halt_active"]:
        all_warnings.append(daily_halt["message"])
    all_warnings.extend(sectors.get("warnings", []))
    if heat["level"] == "HIGH":
        all_warnings.append(f"Portfolio heat is HIGH ({heat['total_heat']:.2%})")

    return {
        "as_of": datetime.now().isoformat(),
        "portfolio_value": round(total_value, 2),
        "cash": round(data["cash"], 2),
        "deployment_pct": round(deployment_pct, 4),
        "stop_losses": stop_losses,
        "daily_halt": daily_halt,
        "heat": heat,
        "sector_concentration": sectors,
        "warnings": all_warnings,
        "risk_level": "HIGH" if all_warnings else "OK",
    }


def record_daily_snapshot():
    """Record today's portfolio value snapshot (idempotent)."""
    _init_snapshots()
    data = _get_portfolio_data()

    total_market = 0
    for h in data["holdings"]:
        price = _get_current_price(h["symbol"]) or h["avg_cost"]
        total_market += h["shares"] * price

    total_value = data["cash"] + total_market
    today = date.today().isoformat()

    # Get previous snapshot for daily P&L
    conn = _get_conn()
    prev = conn.execute(
        "SELECT total_value FROM daily_snapshots WHERE snapshot_date < ? ORDER BY snapshot_date DESC LIMIT 1",
        (today,),
    ).fetchone()

    daily_pnl = 0
    daily_pnl_pct = 0
    if prev:
        daily_pnl = total_value - prev["total_value"]
        daily_pnl_pct = daily_pnl / prev["total_value"] if prev["total_value"] > 0 else 0

    conn.execute("""
        INSERT INTO daily_snapshots (snapshot_date, total_value, cash_balance, market_value, daily_pnl, daily_pnl_pct, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_date) DO UPDATE SET
            total_value = excluded.total_value,
            cash_balance = excluded.cash_balance,
            market_value = excluded.market_value,
            daily_pnl = excluded.daily_pnl,
            daily_pnl_pct = excluded.daily_pnl_pct,
            created_at = excluded.created_at
    """, (today, total_value, data["cash"], total_market, daily_pnl, daily_pnl_pct, datetime.now().isoformat()))
    conn.commit()
    conn.close()

    return {
        "snapshot_date": today,
        "total_value": round(total_value, 2),
        "cash": round(data["cash"], 2),
        "market_value": round(total_market, 2),
        "daily_pnl": round(daily_pnl, 2),
        "daily_pnl_pct": round(daily_pnl_pct, 4),
    }


def main():
    parser = argparse.ArgumentParser(description="Portfolio risk management")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("check", help="Full risk check")
    sub.add_parser("stop-losses", help="Check stop-loss alerts")
    sub.add_parser("report", help="Full risk report (same as check)")
    sub.add_parser("snapshot", help="Record daily portfolio snapshot")

    buy_check = sub.add_parser("check-buy", help="Check if a BUY is allowed")
    buy_check.add_argument("--symbol", required=True)
    buy_check.add_argument("--amount", type=float, required=True, help="Amount in THB")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.command in ("check", "report"):
        result = check_portfolio_risk()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "stop-losses":
        result = check_stop_losses()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "snapshot":
        result = record_daily_snapshot()
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    elif args.command == "check-buy":
        result = check_position_limits(args.symbol, args.amount)
        print(json.dumps(result, default=str, ensure_ascii=False, indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
