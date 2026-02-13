"""SET Stock List — Download and cache the full list of SET-listed stocks."""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CACHE_FILE = PROJECT_ROOT / "data" / "set_all_stocks.json"
CACHE_MAX_DAYS = 7

# SET website endpoints
SET_STOCK_URL = "https://www.set.or.th/en/market/get-quote/stock/setindex"
SET_MAI_URL = "https://www.set.or.th/en/market/get-quote/stock/maiindex"

# Patterns for warrants, derivatives, preferred shares, etc.
EXCLUDE_SUFFIXES = re.compile(r"-[WRPFU]$|[-]F$", re.IGNORECASE)


def _fetch_set_stocks_api() -> list[dict]:
    """Fetch SET stock list from SET's JSON API endpoint."""
    stocks = []

    # SET provides a JSON API for stock listing
    api_url = "https://www.set.or.th/api/set/stock/list"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
        "Referer": "https://www.set.or.th/en/market/get-quote/stock/setindex",
    }

    with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
        # Try the JSON API first
        try:
            resp = client.get(api_url)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                for item in data:
                    symbol = item.get("symbol", "").strip()
                    if not symbol or EXCLUDE_SUFFIXES.search(symbol):
                        continue
                    stocks.append({
                        "symbol": symbol,
                        "name": item.get("name", ""),
                        "market": item.get("market", "SET"),
                        "industry": item.get("industry", ""),
                        "sector": item.get("sector", ""),
                    })
                if stocks:
                    return stocks
        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as e:
            logger.warning("SET JSON API failed: %s, trying HTML fallback", e)

        # Fallback: scrape the HTML page
        stocks = _fetch_set_stocks_html(client)

    return stocks


def _fetch_set_stocks_html(client: httpx.Client) -> list[dict]:
    """Fallback: scrape SET stock list from HTML pages."""
    stocks = []
    urls = [SET_STOCK_URL]

    for url in urls:
        try:
            resp = client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Look for stock data in table rows or script/JSON embeds
            for script in soup.find_all("script"):
                text = script.string or ""
                if "stockData" in text or "symbol" in text:
                    # Try to extract JSON from embedded script
                    match = re.search(r'\[{.*?"symbol".*?}\]', text, re.DOTALL)
                    if match:
                        try:
                            items = json.loads(match.group())
                            for item in items:
                                symbol = item.get("symbol", "").strip()
                                if not symbol or EXCLUDE_SUFFIXES.search(symbol):
                                    continue
                                stocks.append({
                                    "symbol": symbol,
                                    "name": item.get("name", ""),
                                    "market": item.get("market", "SET"),
                                    "industry": item.get("industry", ""),
                                    "sector": item.get("sector", ""),
                                })
                        except json.JSONDecodeError:
                            continue

            # Also try table parsing
            for table in soup.find_all("table"):
                rows = table.find_all("tr")
                for row in rows[1:]:  # skip header
                    cells = row.find_all("td")
                    if len(cells) >= 2:
                        symbol = cells[0].get_text(strip=True).upper()
                        if not symbol or EXCLUDE_SUFFIXES.search(symbol):
                            continue
                        if not re.match(r"^[A-Z][A-Z0-9]{0,7}$", symbol):
                            continue
                        name = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        stocks.append({
                            "symbol": symbol,
                            "name": name,
                            "market": "SET",
                            "industry": "",
                            "sector": "",
                        })

        except httpx.HTTPError as e:
            logger.error("Failed to fetch %s: %s", url, e)

    return stocks


def _fetch_set_stocks_yfinance() -> list[dict]:
    """Last resort: get a known list of major SET stocks via yfinance validation.

    This uses a curated seed list of well-known SET tickers.
    Not comprehensive but ensures we always have something to work with.
    """
    # Comprehensive list of SET50 + SET100 + popular mid-caps
    # This is a curated seed list — the API/HTML scrapers should provide the full list
    seed_symbols = [
        # SET50 (top market cap)
        "PTT", "ADVANC", "AOT", "CPALL", "GULF", "KBANK", "SCB", "SCC", "BDMS", "DELTA",
        "TRUE", "PTTEP", "PTTGC", "BANPU", "BCP", "TOP", "IRPC", "GPSC", "OR",
        "BBL", "KTB", "TTB", "TISCO", "KKP", "TIDLOR",
        "MINT", "CPN", "CRC", "HMPRO", "BJC", "MAKRO", "COM7",
        "BTS", "BEM", "AAV", "BA",
        "BH", "BCH", "CHG", "RAM", "RJH", "BCPG",
        "INTUCH", "DIF", "BTSGIF", "JASIF",
        "IVL", "SCGP", "TPIPP", "RATCH", "EGCO", "EA", "BGRIM",
        "SAWAD", "MTC", "JMT", "TQM",
        "AWC", "WHA", "AMATA", "LH", "AP", "SC", "SIRI", "SPALI", "ORI", "ANAN",
        "TU", "CBG", "GFPT", "CPF", "KCE",
        "BEAUTY", "JMART", "RS", "PLANB",
        # Additional SET100 and popular stocks
        "STGT", "STEC", "TEAM", "MEGA", "SGP",
        "CENTEL", "ERW", "MOSHI",
        "TVO", "THANI", "NER",
        "BPP", "SSP", "WHAUP",
        "SENA", "PSH", "PRIN",
        "SINGER", "SYNEX", "FORTH",
        "TNR", "OSP", "SABINA",
        "MC", "MAJOR", "MONO",
        "PTTEP", "GGC", "HTC",
        "ASE", "STA", "NRF",
        "AEONTS", "GL", "THREL",
        "STARK", "VGI", "JAS",
        "PPP", "TPBI", "TFG",
        "WPH", "SHR", "CMAN",
        "DOD", "DTAC", "TOA", "DCC",
        "SAT", "SAPPE", "SNP",
        "TKN", "TCAP", "BAM",
        "KSL", "KTIS", "BRRGIF",
        "RATCH", "CKP", "SUPER",
        "DEMCO", "SPCG", "GUNKUL",
        "BLA", "TLI", "THRE",
        "TMB", "LHFG", "KIATNAKIN",
        "SISB", "AMARIN", "NATION",
        "THCOM", "INSET", "AIT",
        "PM", "RCL", "WICE",
        "BCT", "GLOBAL", "ITD",
    ]
    # Deduplicate
    seen = set()
    stocks = []
    for sym in seed_symbols:
        if sym not in seen:
            seen.add(sym)
            stocks.append({
                "symbol": sym,
                "name": "",
                "market": "SET",
                "industry": "",
                "sector": "",
            })
    return stocks


def fetch_stock_list(refresh: bool = False) -> list[dict]:
    """Get the full SET stock list, using cache if available.

    Args:
        refresh: Force refresh even if cache is fresh.

    Returns:
        List of stock dicts with symbol, name, market, industry, sector.
    """
    # Check cache
    if not refresh and CACHE_FILE.exists():
        try:
            cache = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(cache.get("fetched_at", "2000-01-01"))
            if datetime.now() - cached_at < timedelta(days=CACHE_MAX_DAYS):
                logger.info(
                    "Using cached stock list (%d stocks, fetched %s)",
                    len(cache["stocks"]),
                    cache["fetched_at"],
                )
                return cache["stocks"]
            else:
                logger.info("Cache expired (fetched %s), refreshing...", cache["fetched_at"])
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Cache file corrupt: %s, refreshing...", e)

    # Fetch from SET website
    logger.info("Fetching SET stock list from website...")
    stocks = _fetch_set_stocks_api()

    # Filter SET main board only (skip warrants, derivatives, preferred)
    stocks = [s for s in stocks if not EXCLUDE_SUFFIXES.search(s["symbol"])]

    # Deduplicate by symbol
    seen = set()
    unique_stocks = []
    for s in stocks:
        if s["symbol"] not in seen:
            seen.add(s["symbol"])
            unique_stocks.append(s)
    stocks = unique_stocks

    # If web scraping returned too few results, use yfinance seed list as fallback
    if len(stocks) < 50:
        logger.warning(
            "Only got %d stocks from SET website, using seed list fallback",
            len(stocks),
        )
        seed_stocks = _fetch_set_stocks_yfinance()
        existing_symbols = {s["symbol"] for s in stocks}
        for s in seed_stocks:
            if s["symbol"] not in existing_symbols:
                stocks.append(s)
                existing_symbols.add(s["symbol"])

    # Save to cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    cache_data = {
        "fetched_at": datetime.now().isoformat(),
        "count": len(stocks),
        "source": "set.or.th",
        "stocks": stocks,
    }
    CACHE_FILE.write_text(json.dumps(cache_data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Saved %d stocks to %s", len(stocks), CACHE_FILE)

    return stocks


def get_symbols(refresh: bool = False) -> list[str]:
    """Get just the symbol strings.

    Args:
        refresh: Force refresh the stock list.

    Returns:
        List of ticker symbols.
    """
    return [s["symbol"] for s in fetch_stock_list(refresh=refresh)]


def main():
    parser = argparse.ArgumentParser(description="Download full SET stock list")
    parser.add_argument("--refresh", action="store_true", help="Force refresh even if cache is fresh")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    stocks = fetch_stock_list(refresh=args.refresh)
    print(f"\nTotal SET stocks: {len(stocks)}")
    print(f"Cache file: {CACHE_FILE}")

    # Show summary by market/sector
    sectors = {}
    for s in stocks:
        sector = s.get("sector") or s.get("industry") or "Unknown"
        sectors.setdefault(sector, []).append(s["symbol"])

    if any(s != "Unknown" for s in sectors):
        print("\nBy sector:")
        for sector, syms in sorted(sectors.items(), key=lambda x: -len(x[1])):
            print(f"  {sector}: {len(syms)} stocks")

    # Print first 20
    print(f"\nFirst 20 symbols: {', '.join(s['symbol'] for s in stocks[:20])}")


if __name__ == "__main__":
    main()
