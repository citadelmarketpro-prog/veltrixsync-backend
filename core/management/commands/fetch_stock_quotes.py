"""
Fetch live stock quotes + market index values from FMP.
FMP stable API only supports single-symbol calls for stocks,
so we use ThreadPoolExecutor for parallel fetches.
Indices are fetched from FMP /quotes/index (batch, one call).
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from core.models import StockQuote
from core import fmp_client

STOCK_SYMBOLS = [
    # Technology
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "NFLX",
    "AMD", "ORCL", "CSCO", "ADBE", "INTC", "QCOM", "AVGO", "CRM",
    # Finance
    "JPM", "BAC", "GS", "V", "MA", "WFC", "BLK", "AXP", "MS", "C",
    # Healthcare
    "JNJ", "PFE", "UNH", "LLY", "ABBV", "MRK", "AMGN", "ABT", "TMO", "CVS",
    # Energy
    "XOM", "CVX", "COP", "SLB", "EOG", "OXY",
    # Consumer
    "WMT", "COST", "HD", "MCD", "NKE", "DIS", "KO", "PG", "SBUX", "TGT",
    # Industrials
    "BA", "CAT", "GE", "RTX", "HON", "UPS", "DE", "MMM",
]

# FMP symbol → internal DB symbol (is_index=True)
# FMP /quotes/index returns symbols like "^GSPC", "^DJI", "^IXIC", "^FTSE"
INDEX_FMP_MAP = {
    "^GSPC":  "SP500",    # S&P 500
    "^DJI":   "DJIA",     # Dow Jones
    "^IXIC":  "NASDAQ",   # NASDAQ Composite
    "^FTSE":  "FTSE100",  # FTSE 100
    # Without caret — some FMP plans return these without it
    "GSPC":   "SP500",
    "DJI":    "DJIA",
    "IXIC":   "NASDAQ",
    "FTSE":   "FTSE100",
}

# Old ETF proxy symbols from previous version — delete on first run
_OLD_ETF_SYMBOLS = ["SPY", "QQQ", "DIA", "EWU"]


def _fetch_quote(sym: str):
    """Fetch /quote for a single stock symbol via FMP. Returns (sym, dict|None)."""
    try:
        data = fmp_client.fmp_get("/quote", {"symbol": sym})
        if isinstance(data, list) and data:
            return sym, data[0]
        return sym, None
    except Exception:
        return sym, None


class Command(BaseCommand):
    help = "Fetch live stock quotes and index values from FMP. Run every 10–15 min."

    def handle(self, *args, **options):
        # Remove old ETF proxy records
        deleted, _ = StockQuote.objects.filter(
            symbol__in=_OLD_ETF_SYMBOLS, is_index=True
        ).delete()
        if deleted:
            self.stdout.write(f"Removed {deleted} old ETF proxy record(s).")

        self._fetch_stock_quotes()
        self._fetch_index_quotes()

    # ── stocks ────────────────────────────────────────────────────────────────

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

    # ── indices ───────────────────────────────────────────────────────────────

    def _fetch_index_quotes(self):
        all_indices = []

        # Attempt 1: stable batch — comma-separated caret symbols
        try:
            data = fmp_client.fmp_get("/quote", {"symbol": "^GSPC,^DJI,^IXIC,^FTSE"})
            if isinstance(data, list) and data:
                all_indices = data
        except Exception as exc:
            self.stderr.write(f"Stable batch index failed: {exc}")

        # Attempt 2: FMP v3 /quotes/index (requires Starter+ plan)
        if not all_indices:
            try:
                data = fmp_client.fmp_get_v3("/quotes/index")
                if isinstance(data, list) and data:
                    all_indices = data
            except Exception as exc:
                self.stderr.write(f"v3 /quotes/index failed: {exc}")

        # Attempt 3: individual stable /quote calls per symbol
        if not all_indices:
            self.stderr.write("Falling back to individual index symbol calls...")
            for fmp_sym in ("^GSPC", "^DJI", "^IXIC", "^FTSE"):
                try:
                    data = fmp_client.fmp_get("/quote", {"symbol": fmp_sym})
                    if isinstance(data, list):
                        all_indices.extend(data)
                except Exception:
                    pass

        if not all_indices:
            self.stderr.write("All index fetch attempts failed.")
            return

        updated = errors = skipped = 0
        seen = set()

        for item in all_indices:
            fmp_sym = item.get("symbol", "")
            internal = INDEX_FMP_MAP.get(fmp_sym)
            if not internal or internal in seen:
                continue
            seen.add(internal)

            try:
                price = float(item.get("price") or 0)
                if price <= 0:
                    skipped += 1
                    continue
                StockQuote.objects.update_or_create(
                    symbol=internal,
                    defaults={
                        "price":      Decimal(str(price)),
                        "change":     Decimal(str(item.get("change") or 0)),
                        "change_pct": Decimal(
                            str(item.get("changePercentage") or item.get("changesPercentage") or 0)
                        ),
                        "volume":     int(item.get("volume") or 0),
                        "market_cap": 0,
                        "pe":         None,
                        "eps":        Decimal("0"),
                        "is_index":   True,
                    },
                )
                updated += 1
            except (InvalidOperation, Exception) as exc:
                self.stderr.write(f"Error saving index {internal}: {exc}")
                errors += 1

        if not seen:
            self.stderr.write(
                f"No matching index symbols in FMP response ({len(all_indices)} items). "
                "Expected ^GSPC, ^DJI, ^IXIC, ^FTSE."
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Index quotes: {updated} updated, {errors} errors, {skipped} skipped"
            )
        )
