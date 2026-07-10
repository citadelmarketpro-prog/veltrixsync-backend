from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from core.models import CryptoPrice
from core import fmp_client

# FMP crypto symbol → our wallet symbol
SYMBOL_MAP = {
    "BTCUSD":   "BTC",
    "ETHUSD":   "ETH",
    "USDTUSD":  "USDT",
    "BNBUSD":   "BNB",
    "USDCUSD":  "USDC",
    "LTCUSD":   "LTC",
    "XRPUSD":   "XRP",
    "SOLUSD":   "SOL",
    "DOGEUSD":  "DOGE",
    "TRXUSD":   "TRX",
    "MATICUSD": "MATIC",
    "AVAXUSD":  "AVAX",
    "BCHUSD":   "BCH",
}


class Command(BaseCommand):
    help = "Fetch current crypto prices from FMP and store them for deposit unit calculation."

    def handle(self, *args, **options):
        try:
            quotes = fmp_client.get_crypto_quotes()
        except Exception as exc:
            self.stderr.write(f"FMP request failed: {exc}")
            return

        if not isinstance(quotes, list):
            self.stderr.write(f"Unexpected response: {quotes}")
            return

        updated = skipped = 0
        for q in quotes:
            fmp_sym = q.get("symbol", "")
            local_sym = SYMBOL_MAP.get(fmp_sym)
            if not local_sym:
                continue

            raw_price = q.get("price") or q.get("previousClose") or 0
            try:
                price = Decimal(str(raw_price))
            except InvalidOperation:
                continue

            if price <= 0:
                skipped += 1
                continue

            CryptoPrice.objects.update_or_create(
                symbol=local_sym,
                defaults={"price_usd": price},
            )
            updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"Crypto prices: {updated} updated, {skipped} skipped (zero/invalid price)")
        )
