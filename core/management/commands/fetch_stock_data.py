"""
Fetch stock profiles + 20-day sparkline history from FMP.
Run once daily — profiles and history change slowly.
FMP stable API only supports single-symbol calls for /profile and
/historical-price-eod/short, so we use ThreadPoolExecutor throughout.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand

from core.models import StockHistory, StockProfile
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

# FMP sector names → our frontend filter labels
SECTOR_NORM = {
    "Financial Services":     "Finance",
    "Consumer Cyclical":      "Consumer",
    "Consumer Defensive":     "Consumer",
    "Communication Services": "Technology",
}


def _parse_52w(range_str: str):
    """Parse FMP '201.5-317.4' range string → (low, high) Decimals."""
    try:
        # Some entries may look like "1,234.5-2,345.6" — strip commas first
        clean = str(range_str or "").replace(",", "")
        parts = clean.split("-")
        if len(parts) == 2:
            return Decimal(parts[0].strip()), Decimal(parts[1].strip())
    except (InvalidOperation, ValueError):
        pass
    return Decimal(0), Decimal(0)


def _domain_from_url(url: str) -> str:
    return (
        url.replace("https://", "")
           .replace("http://", "")
           .replace("www.", "")
           .rstrip("/")
           .split("/")[0]
    )


def _fetch_profile(sym: str):
    """Fetch /profile for a single symbol. Returns (sym, dict|None)."""
    try:
        data = fmp_client.fmp_get("/profile", {"symbol": sym})
        if isinstance(data, list) and data:
            return sym, data[0]
        return sym, None
    except Exception:
        return sym, None


def _build_sparkline(price: float, pct_1d: float, pct_5d: float, pct_1m: float) -> list:
    """
    Reconstruct a 20-point price sparkline from percentage changes.
    FMP stable has no EOD history endpoint, so we interpolate between
    anchor prices derived from the 1D/5D/1M change percentages.
    Output: oldest (index 0) → newest (index 19).
    """
    p_today = price
    p_1d    = price / (1 + pct_1d / 100) if pct_1d != -100 else price
    p_5d    = price / (1 + pct_5d / 100) if pct_5d != -100 else price
    p_1m    = price / (1 + pct_1m / 100) if pct_1m != -100 else price

    # 20 points: index 0 = ~19 trading days ago, index 19 = today
    points = []
    for i in range(20):
        day = 19 - i  # 19, 18, ..., 1, 0  (0 = today)
        if day == 0:
            p = p_today
        elif day <= 1:
            t = day / 1.0
            p = p_today + (p_1d - p_today) * t
        elif day <= 5:
            t = (day - 1) / 4.0
            p = p_1d + (p_5d - p_1d) * t
        else:
            t = (day - 5) / 14.0
            p = p_5d + (p_1m - p_5d) * t
        points.append(round(p, 4))
    return points


def _fetch_history(sym: str):
    """
    Fetch /stock-price-change and reconstruct a 20-point sparkline.
    Also needs the current price — fetch /quote alongside.
    Returns (sym, list|None).
    """
    try:
        changes = fmp_client.get_stock_price_change(sym)
        if not changes:
            return sym, None
        quote = fmp_client.fmp_get("/quote", {"symbol": sym})
        price = float((quote[0].get("price") or 0) if isinstance(quote, list) and quote else 0)
        if price <= 0:
            return sym, None
        pct_1d = float(changes.get("1D") or 0)
        pct_5d = float(changes.get("5D") or 0)
        pct_1m = float(changes.get("1M") or 0)
        return sym, _build_sparkline(price, pct_1d, pct_5d, pct_1m)
    except Exception:
        return sym, None


class Command(BaseCommand):
    help = "Fetch stock profiles and sparkline history from FMP (run daily)."

    def handle(self, *args, **options):
        self._fetch_profiles()
        self._fetch_history()

    # ── profiles ──────────────────────────────────────────────────────────────

    def _fetch_profiles(self):
        profiles = {}
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_fetch_profile, sym): sym for sym in STOCK_SYMBOLS}
            for future in as_completed(futures):
                sym, data = future.result()
                if data:
                    profiles[sym] = data

        if not profiles:
            self.stderr.write("No profiles received — check FMP API key or network.")
            return

        updated = errors = 0
        for sym, p in profiles.items():
            try:
                low_52w, high_52w = _parse_52w(p.get("range", ""))
                website = p.get("website") or ""
                domain  = _domain_from_url(website) if website else ""

                # stable API: "averageVolume" (not "volAvg"), "lastDividend" (not dividendYield%)
                raw_sector = p.get("sector") or ""
                sector = SECTOR_NORM.get(raw_sector, raw_sector)

                StockProfile.objects.update_or_create(
                    symbol=sym,
                    defaults={
                        "name":        p.get("companyName") or sym,
                        "sector":      sector,
                        "exchange":    p.get("exchange") or p.get("exchangeFullName") or "",
                        "domain":      domain,
                        "logo_url":    p.get("image") or "",
                        "description": p.get("description") or "",
                        "high_52w":    high_52w,
                        "low_52w":     low_52w,
                        # lastDividend is a dollar amount per share (not a % yield)
                        "div_yield":   Decimal(str(p.get("lastDividend") or 0)),
                        "beta":        Decimal(str(p.get("beta") or 0)),
                        "avg_vol":     int(p.get("averageVolume") or 0),
                    },
                )
                updated += 1
            except Exception as exc:
                self.stderr.write(f"Profile error for {sym}: {exc}")
                errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"Stock profiles: {updated} updated, {errors} errors")
        )

    # ── sparkline history ─────────────────────────────────────────────────────

    def _fetch_history(self):
        updated = errors = 0
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = {pool.submit(_fetch_history, sym): sym for sym in STOCK_SYMBOLS}
            for future in as_completed(futures):
                sym, prices = future.result()
                if prices:
                    StockHistory.objects.update_or_create(
                        symbol=sym,
                        defaults={"prices": prices},
                    )
                    updated += 1
                else:
                    errors += 1

        self.stdout.write(
            self.style.SUCCESS(f"Stock history: {updated} updated, {errors} errors")
        )
