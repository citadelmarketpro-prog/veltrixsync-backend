"""
Fetch live stock quotes (FMP) + market index values (Yahoo Finance).
FMP stable API only supports single-symbol calls, so we use ThreadPoolExecutor.
Indices use Yahoo Finance because FMP stable doesn't support ^GSPC etc.
"""
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from core.models import StockQuote
from core import fmp_client

STOCK_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA",
    "META", "JPM", "JNJ", "XOM", "NFLX", "V",
    "BA", "PFE", "CAT", "WMT",
]

# Internal symbol → Yahoo Finance ticker
# Stored in DB with is_index=True; matched by _INDEX_NAMES in views.py
INDEX_CONFIG = [
    ("SP500",   "^GSPC"),   # S&P 500
    ("NASDAQ",  "^IXIC"),   # NASDAQ Composite
    ("DJIA",    "^DJI"),    # Dow Jones Industrial Average
    ("FTSE100", "^FTSE"),   # FTSE 100
]

# Old ETF proxy symbols from previous version — delete them on first run
_OLD_ETF_SYMBOLS = ["SPY", "QQQ", "DIA", "EWU"]

_YF_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _fetch_quote(sym: str):
    """Fetch /quote for a single stock symbol via FMP. Returns (sym, dict|None)."""
    try:
        data = fmp_client.fmp_get("/quote", {"symbol": sym})
        if isinstance(data, list) and data:
            return sym, data[0]
        return sym, None
    except Exception:
        return sym, None


def _fetch_yahoo_index(internal_sym: str, yahoo_sym: str):
    """
    Fetch current price + daily change for a market index from Yahoo Finance.
    Returns (internal_sym, dict|None).
    """
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_sym}"
        resp = requests.get(
            url,
            params={"range": "2d", "interval": "1d"},
            headers=_YF_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        result = data["chart"]["result"][0]
        meta = result["meta"]
        price = float(meta.get("regularMarketPrice") or 0)
        prev  = float(
            meta.get("chartPreviousClose")
            or meta.get("previousClose")
            or price
        )
        if price <= 0:
            return internal_sym, None
        change = price - prev
        change_pct = (change / prev * 100) if prev else 0
        return internal_sym, {
            "price":      price,
            "change":     change,
            "change_pct": change_pct,
        }
    except Exception:
        return internal_sym, None


class Command(BaseCommand):
    help = "Fetch live stock quotes (FMP) and index values (Yahoo Finance). Run every 10–15 min."

    def handle(self, *args, **options):
        # Remove old ETF proxy records from the index section
        deleted, _ = StockQuote.objects.filter(
            symbol__in=_OLD_ETF_SYMBOLS, is_index=True
        ).delete()
        if deleted:
            self.stdout.write(f"Removed {deleted} old ETF proxy record(s).")

        self._fetch_stock_quotes()
        self._fetch_index_quotes()

    # ── stocks (FMP) ──────────────────────────────────────────────────────────

    def _fetch_stock_quotes(self):
        quotes = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_quote, sym): sym for sym in STOCK_SYMBOLS}
            for future in as_completed(futures):
                sym, data = future.result()
                if data:
                    quotes[sym] = data

        updated = errors = 0
        for sym, q in quotes.items():
            try:
                StockQuote.objects.update_or_create(
                    symbol=sym,
                    defaults={
                        "price":      Decimal(str(q.get("price") or 0)),
                        "change":     Decimal(str(q.get("change") or 0)),
                        "change_pct": Decimal(str(q.get("changePercentage") or 0)),
                        "volume":     int(q.get("volume") or 0),
                        "market_cap": int(q.get("marketCap") or 0),
                        "pe":         None,
                        "eps":        Decimal("0"),
                        "is_index":   False,
                    },
                )
                updated += 1
            except (InvalidOperation, Exception) as exc:
                self.stderr.write(f"Error saving {sym}: {exc}")
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"Stock quotes: {updated} updated, {errors} errors")
        )

    # ── indices (Yahoo Finance) ───────────────────────────────────────────────

    def _fetch_index_quotes(self):
        updated = errors = 0
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = {
                pool.submit(_fetch_yahoo_index, sym, yahoo): sym
                for sym, yahoo in INDEX_CONFIG
            }
            for future in as_completed(futures):
                sym, data = future.result()
                if not data:
                    self.stderr.write(f"Index fetch failed: {sym}")
                    errors += 1
                    continue
                try:
                    StockQuote.objects.update_or_create(
                        symbol=sym,
                        defaults={
                            "price":      Decimal(str(data["price"])),
                            "change":     Decimal(str(data["change"])),
                            "change_pct": Decimal(str(data["change_pct"])),
                            "volume":     0,
                            "market_cap": 0,
                            "pe":         None,
                            "eps":        Decimal("0"),
                            "is_index":   True,
                        },
                    )
                    updated += 1
                except (InvalidOperation, Exception) as exc:
                    self.stderr.write(f"Error saving index {sym}: {exc}")
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"Index quotes: {updated} updated, {errors} errors")
        )
