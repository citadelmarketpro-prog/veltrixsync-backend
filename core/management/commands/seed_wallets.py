"""
python manage.py seed_wallets

Populates AdminWallet with one entry per wallet type using randomly generated
addresses that resemble real-format addresses for each network.

Run in development only — never seed real addresses this way.
"""

import random
import string

from django.core.management.base import BaseCommand

from core.models import AdminWallet


def _btc_address():
    """Simulated Bitcoin P2PKH address (34 chars, starts with 1)."""
    chars = string.ascii_letters + string.digits
    return "1" + "".join(random.choices(chars, k=33))


def _eth_address():
    """Simulated Ethereum / ERC20 / BEP20 / Polygon / Avalanche address."""
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))


def _tron_address():
    """Simulated TRON address (starts with T, 34 chars)."""
    chars = string.ascii_letters + string.digits
    return "T" + "".join(random.choices(chars, k=33))


def _sol_address():
    """Simulated Solana base58 address (44 chars)."""
    chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    return "".join(random.choices(chars, k=44))


def _xrp_address():
    """Simulated XRP classic address (starts with r, ~34 chars)."""
    chars = string.ascii_letters + string.digits
    return "r" + "".join(random.choices(chars, k=33))


def _ltc_address():
    """Simulated Litecoin address (starts with L, 34 chars)."""
    chars = string.ascii_letters + string.digits
    return "L" + "".join(random.choices(chars, k=33))


def _doge_address():
    """Simulated Dogecoin address (starts with D, 34 chars)."""
    chars = string.ascii_letters + string.digits
    return "D" + "".join(random.choices(chars, k=33))


def _bch_address():
    """Simulated Bitcoin Cash cashaddr (starts with bitcoincash:q)."""
    chars = "0123456789abcdefghjkmnpqrstuvwxyz"
    return "bitcoincash:q" + "".join(random.choices(chars, k=41))


# Map wallet type → address generator
_ADDRESS_GENERATORS = {
    "bitcoin":       _btc_address,
    "ethereum":      _eth_address,
    "usdt_trc20":    _tron_address,
    "usdt_erc20":    _eth_address,
    "bnb":           _eth_address,
    "usdc":          _eth_address,
    "litecoin":      _ltc_address,
    "ripple":        _xrp_address,
    "solana":        _sol_address,
    "dogecoin":      _doge_address,
    "tron":          _tron_address,
    "polygon":       _eth_address,
    "avalanche":     _eth_address,
    "bitcoin_cash":  _bch_address,
}


class Command(BaseCommand):
    help = "Seed AdminWallet with one entry per supported wallet type."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing AdminWallet entries before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = AdminWallet.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} existing wallet(s)."))

        created_count = 0
        for order, (wallet_type, _) in enumerate(AdminWallet.WALLET_TYPE_CHOICES):
            if AdminWallet.objects.filter(name=wallet_type).exists():
                self.stdout.write(f"  skip  {wallet_type} (already exists)")
                continue

            address_fn = _ADDRESS_GENERATORS.get(wallet_type, _eth_address)
            wallet = AdminWallet(
                name=wallet_type,
                address=address_fn(),
                is_active=True,
                order=order,
                # symbol / network auto-filled by model.save()
            )
            wallet.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"  created  {wallet.get_name_display()} ({wallet.symbol}) — {wallet.address[:30]}…"
                )
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created_count} wallet(s) created."))
