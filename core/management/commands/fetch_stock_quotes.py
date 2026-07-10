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

# ETF proxies for market index bar (^GSPC etc. not supported by stable API)
INDEX_SYMBOLS = ["SPY", "QQQ", "DIA", "EWU"]


def _fetch_quote(sym: str):
    """Fetch /quote for a single symbol. Returns (sym, dict|None)."""
    try:
        data = fmp_client.fmp_get("/quote", {"symbol": sym})
        if isinstance(data, list) and data:
            return sym, data[0]
        return sym, None
    except Exception as exc:
        return sym, None


class Command(BaseCommand):
    help = "Fetch live stock and index quotes from FMP (run every 10–15 min)."

    def handle(self, *args, **options):
        all_symbols = STOCK_SYMBOLS + INDEX_SYMBOLS
        index_set   = set(INDEX_SYMBOLS)

        quotes = {}
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(_fetch_quote, sym): sym for sym in all_symbols}
            for future in as_completed(futures):
                sym, data = future.result()
                if data:
                    quotes[sym] = data

        if not quotes:
            self.stderr.write("No quotes received — check FMP API key or network.")
            return

        updated = errors = 0
        for sym, q in quotes.items():
            try:
                StockQuote.objects.update_or_create(
                    symbol=sym,
                    defaults={
                        "price":      Decimal(str(q.get("price") or 0)),
                        "change":     Decimal(str(q.get("change") or 0)),
                        # stable API uses "changePercentage" (not "changesPercentage")
                        "change_pct": Decimal(str(q.get("changePercentage") or 0)),
                        "volume":     int(q.get("volume") or 0),
                        "market_cap": int(q.get("marketCap") or 0),
                        "pe":         None,   # not provided by /quote stable endpoint
                        "eps":        Decimal("0"),
                        "is_index":   sym in index_set,
                    },
                )
                updated += 1
            except (InvalidOperation, Exception) as exc:
                self.stderr.write(f"Error saving {sym}: {exc}")
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"Stock quotes: {updated} updated, {errors} errors")
        )
