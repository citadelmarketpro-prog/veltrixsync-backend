from decimal import Decimal, InvalidOperation

import requests
from django.core.management.base import BaseCommand

from core.models import CryptoPrice

# CoinGecko ID → our wallet symbol
# Free API, no key required: https://api.coingecko.com/api/v3/simple/price
COINGECKO_MAP = {
    "bitcoin":       "BTC",
    "ethereum":      "ETH",
    "tether":        "USDT",
    "binancecoin":   "BNB",
    "usd-coin":      "USDC",
    "litecoin":      "LTC",
    "ripple":        "XRP",
    "solana":        "SOL",
    "dogecoin":      "DOGE",
    "tron":          "TRX",
    "matic-network": "MATIC",
    "avalanche-2":   "AVAX",
    "bitcoin-cash":  "BCH",
}

_CG_URL = "https://api.coingecko.com/api/v3/simple/price"


class Command(BaseCommand):
    help = "Fetch current crypto prices from CoinGecko (free, no key) for deposit unit calculation."

    def handle(self, *args, **options):
        ids = ",".join(COINGECKO_MAP.keys())
        try:
            resp = requests.get(
                _CG_URL,
                params={"ids": ids, "vs_currencies": "usd"},
                timeout=15,
                headers={"Accept": "application/json"},
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:
            self.stderr.write(f"CoinGecko request failed: {exc}")
            return

        if not isinstance(data, dict):
            self.stderr.write(f"Unexpected response: {data}")
            return

        updated = skipped = 0
        for cg_id, local_sym in COINGECKO_MAP.items():
            entry = data.get(cg_id, {})
            raw_price = entry.get("usd", 0)
            try:
                price = Decimal(str(raw_price))
            except InvalidOperation:
                skipped += 1
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
            self.style.SUCCESS(
                f"Crypto prices: {updated} updated, {skipped} skipped (zero/invalid price)"
            )
        )
