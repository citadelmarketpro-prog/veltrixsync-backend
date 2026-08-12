"""
Random-but-plausible demo data for freshly created traders.

Auto-seeds the child tables shown on the trader detail page — Top Assets,
Portfolio Allocation, Open Positions, Trade History — with a handful of rows
each, spread across recent (this month / last month / two months ago) dates,
plus fills in any Trader-level summary stat still at its default (0) so the
profile doesn't look empty. Everything created here is a normal row
afterwards: editable and deletable exactly like data an admin added by hand.

Data sources:
- Top Assets: live quotes from the FMP API (real symbol, name, % change)
  when reachable, falling back to the local JSON pool otherwise.
- Portfolio Allocation / Open Positions / Trade History: drawn from a JSON
  pool of realistic instruments (dashboard/trader_seed_data.json) rather than
  fully arbitrary numbers, so combinations look like real market data and
  differ from trader to trader.

The "Copiers" tab on the frontend is backed by `DummyCopier` — a display-only
model with no link to real accounts (just a free-text name) — NOT the real
`CopyRelationship` table, which represents actual users who chose to copy a
trader and is never touched here.
"""

import json
import random
import time
from datetime import timedelta
from pathlib import Path

import requests
from django.db.models import Max
from django.utils import timezone

from core.models import DummyCopier, PortfolioAllocation, TraderAsset, TraderPosition, TradeHistory, TraderSection

_DATA_PATH = Path(__file__).resolve().parent / "trader_seed_data.json"
_data_cache = None


def _seed_data() -> dict:
    """Load+cache the JSON pool of realistic instruments/labels used for seeding."""
    global _data_cache
    if _data_cache is None:
        with open(_DATA_PATH, encoding="utf-8") as f:
            _data_cache = json.load(f)
    return _data_cache


# ─────────────────────────────────────────────────────────────────────────────
# Recent-date helper — "this month / last month / two months ago"
# ─────────────────────────────────────────────────────────────────────────────

def _recent_datetime(now=None):
    """A random datetime that recently 'happened' — spread across three
    buckets (this month, last month, two months ago) so a set of rows don't
    all cluster on the same day."""
    now = now or timezone.now()
    bucket = random.choice([0, 1, 2])  # 0=this month, 1=last month, 2=two months ago
    dt = now - timedelta(days=bucket * 30 + random.randint(0, 29), hours=random.randint(0, 23), minutes=random.randint(0, 59))
    return min(dt, now)


# ─────────────────────────────────────────────────────────────────────────────
# Top Assets — live FMP quotes, falling back to the JSON pool
# ─────────────────────────────────────────────────────────────────────────────

# Deliberately wide candidate pools — every trader picks a random 6 out of ~75
# symbols here (plus another ~75 in the JSON fallback pool below), so Top
# Assets actually differ trader to trader instead of converging on the same
# handful of big names.
_FMP_CRYPTO_SYMBOLS = [
    "BTCUSD", "ETHUSD", "SOLUSD", "BNBUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "DOTUSD",
    "AVAXUSD", "MATICUSD", "LTCUSD", "LINKUSD", "UNIUSD", "ATOMUSD", "TRXUSD",
    "NEARUSD", "APTUSD", "ARBUSD", "SHIBUSD", "XLMUSD", "ETCUSD", "FILUSD",
]
_FMP_STOCK_SYMBOLS = [
    # Tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "NFLX", "AMD", "INTC",
    "ORCL", "CRM", "ADBE", "CSCO", "IBM", "QCOM", "TXN", "NOW", "SHOP", "UBER",
    # Finance
    "JPM", "BAC", "WFC", "GS", "MS", "V", "MA", "AXP", "C", "BLK", "COIN", "PYPL",
    # Healthcare
    "JNJ", "PFE", "UNH", "ABBV", "MRK", "LLY", "TMO", "ABT",
    # Consumer
    "WMT", "PG", "KO", "PEP", "MCD", "NKE", "SBUX", "DIS", "HD", "COST",
    # Energy / Industrial
    "XOM", "CVX", "BA", "CAT", "GE", "HON",
    # ETFs / Indices
    "SPY", "QQQ", "DIA", "IWM",
]


def _fmp_asset_row(quote: dict) -> dict | None:
    change = quote.get("changePercentage")
    symbol = quote.get("symbol")
    if change is None or not symbol:
        return None
    change = round(float(change), 2)
    ticker = symbol[:-3] if symbol.endswith("USD") and symbol not in ("EURUSD", "GBPUSD", "USDJPY") else symbol
    return {
        "name":         quote.get("name") or ticker,
        "ticker":       ticker,
        "avg_return":   change,
        "avg_risk":     round(abs(change) * random.uniform(0.6, 2.0) + random.uniform(0.5, 3), 2),
        "success_rate": round(min(97, max(42, 68 + change * 2.2)), 2),
    }


def _fetch_fmp_top_assets(n: int, time_budget: float = 6.0) -> list[dict]:
    """Best-effort: fetch up to `n` real quotes from FMP one symbol at a time
    (the current plan doesn't support batched multi-symbol quotes). Returns
    fewer than `n` — or an empty list — if FMP is slow/unreachable/rate-limited;
    the caller tops up any shortfall from the local JSON pool."""
    from core.fmp_client import get_stock_quotes

    candidates = _FMP_CRYPTO_SYMBOLS + _FMP_STOCK_SYMBOLS
    random.shuffle(candidates)

    rows, start = [], time.monotonic()
    for symbol in candidates:
        if len(rows) >= n or (time.monotonic() - start) > time_budget:
            break
        try:
            quotes = get_stock_quotes([symbol])
            if isinstance(quotes, list) and quotes:
                row = _fmp_asset_row(quotes[0])
                if row:
                    rows.append(row)
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 429:
                break  # plan/rate limit hit — stop hammering it, fall back for the rest
            continue   # one bad symbol shouldn't sink the whole batch
        except Exception:
            continue   # network hiccup/timeout on this symbol — try the next one
    return rows


def _top_assets(n: int) -> list[dict]:
    rows = []
    try:
        rows = _fetch_fmp_top_assets(n)
    except Exception:
        rows = []

    if len(rows) < n:
        used = {r["ticker"] for r in rows}
        pool = [a for a in _seed_data()["asset_pool"] if a["ticker"] not in used]
        random.shuffle(pool)
        for a in pool[: n - len(rows)]:
            rows.append({
                "name": a["name"], "ticker": a["ticker"],
                "avg_return":   round(random.uniform(-15, 45), 2),
                "avg_risk":     round(random.uniform(1, 9), 2),
                "success_rate": round(random.uniform(45, 96), 2),
            })
    return rows[:n]


# ─────────────────────────────────────────────────────────────────────────────
# Percentage split helper (Portfolio Allocation always sums to 100)
# ─────────────────────────────────────────────────────────────────────────────

def _split_percentages(n: int, total: int = 100) -> list[int]:
    if n <= 1:
        return [total]
    cuts = sorted(random.sample(range(1, total), n - 1))
    return [cuts[0]] + [cuts[i] - cuts[i - 1] for i in range(1, len(cuts))] + [total - cuts[-1]]


def random_portfolio_allocation_rows(n: int = 6) -> list[dict]:
    """Public helper — also used to reseed allocations from the edit page."""
    pool   = _seed_data()["allocation_pool"]
    picks  = random.sample(pool, min(n, len(pool)))
    pcts   = _split_percentages(len(picks))
    return [
        {"label": p["label"], "pct": pct, "color": p["color"], "order": i}
        for i, (p, pct) in enumerate(zip(picks, pcts))
    ]


def random_dummy_copier_rows(n: int = 6) -> list[dict]:
    """Public helper — display-only fake copiers (DummyCopier), safe to
    regenerate any time since they carry no link to real user accounts."""
    names = random.sample(_seed_data()["copier_names"], min(n, len(_seed_data()["copier_names"])))
    now   = timezone.now()
    rows  = []
    for name in names:
        allocated = round(random.uniform(500, 25000), 2)
        rows.append({
            "name": name,
            "started_at": _recent_datetime(now),
            "allocated_amount": allocated,
            "pl": round(allocated * random.uniform(-0.15, 0.35), 2),
        })
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Default section — makes a new trader visible on the public "Traders" list
# ─────────────────────────────────────────────────────────────────────────────

def assign_default_section(trader, section: str = "rising_stars") -> None:
    """Add the trader to `section` (append at the end) if it isn't already in
    any section — new traders otherwise never show up on the public list."""
    if trader.section_memberships.exists():
        return
    next_rank = (TraderSection.objects.filter(section=section).aggregate(m=Max("rank"))["m"] or 0) + 1
    TraderSection.objects.create(trader=trader, section=section, rank=next_rank)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def seed_trader_demo_data(trader, rows: int = 6, seed_allocations: bool = True, seed_copiers: bool = True) -> None:
    """Populate Top Assets, Open Positions, Trade History and (Dummy) Copiers
    with `rows` random rows each (and Portfolio Allocation too, unless
    `seed_allocations=False`), plus fill any Trader-level summary stat still
    at its default (0)."""
    data = _seed_data()
    now  = timezone.now()

    # ── Top Assets (FMP-backed) ──
    TraderAsset.objects.bulk_create([
        TraderAsset(trader=trader, order=i, **row)
        for i, row in enumerate(_top_assets(rows))
    ])

    # ── Portfolio Allocation ──
    if seed_allocations:
        PortfolioAllocation.objects.bulk_create([
            PortfolioAllocation(trader=trader, **row)
            for row in random_portfolio_allocation_rows(rows)
        ])

    # ── Open Positions ── (opened_at now spreads across recent months)
    position_assets = random.sample(data["asset_pool"], min(rows, len(data["asset_pool"])))
    TraderPosition.objects.bulk_create([
        TraderPosition(
            trader=trader, market=a["ticker"],
            direction=random.choice(data["directions"]),
            invested=round(random.uniform(4, 28), 2),
            pl=round(random.uniform(-12, 30), 2),
            value=round(random.uniform(4, 32), 2),
            sell_price=round(random.uniform(10, 45000), 2),
            buy_price=round(random.uniform(10, 45000), 2),
            opened_at=_recent_datetime(now),
        )
        for a in position_assets
    ])

    # ── Trade History ── (open/close dates spread across recent months)
    history_assets = random.sample(data["asset_pool"], min(rows, len(data["asset_pool"])))
    history_rows = []
    for a in history_assets:
        open_dt     = _recent_datetime(now)
        close_dt    = min(open_dt + timedelta(hours=random.randint(2, 96)), now)
        open_price  = round(random.uniform(10, 45000), 2)
        close_price = round(open_price * random.uniform(0.85, 1.25), 2)
        history_rows.append(TradeHistory(
            trader=trader, name=f"{a['name']} ({a['ticker']})",
            order_type=random.choice(data["order_types"]),
            position=random.choice(data["trade_positions"]),
            open_price=open_price, open_date=open_dt,
            close_price=close_price, close_date=close_dt,
            pl=round(random.uniform(-20, 35), 2),
        ))
    TradeHistory.objects.bulk_create(history_rows)

    # ── Demo Copiers (DummyCopier — display-only, no link to real accounts) ──
    if seed_copiers:
        DummyCopier.objects.bulk_create([
            DummyCopier(trader=trader, **row)
            for row in random_dummy_copier_rows(rows)
        ])

    # ── Trader-level summary stats — only fill what the admin left at 0 ──
    updates = {}
    if trader.roi == 0:             updates["roi"]             = round(random.uniform(5, 65), 2)
    if trader.win_rate == 0:        updates["win_rate"]        = round(random.uniform(50, 92), 2)
    if trader.copiers_count == 0:   updates["copiers_count"]   = random.randint(20, 2500)
    if trader.followers_count == 0: updates["followers_count"] = random.randint(50, 5000)
    if trader.min_capital == 0:     updates["min_capital"]     = random.choice([50, 100, 250, 500, 1000])
    if trader.trading_days == 0:    updates["trading_days"]    = random.randint(60, 900)
    if trader.master_pnl == 0:      updates["master_pnl"]      = round(random.uniform(500, 85000), 2)
    if trader.account_assets == 0:  updates["account_assets"]  = round(random.uniform(2000, 250000), 2)
    if trader.max_drawdown == 0:    updates["max_drawdown"]    = round(random.uniform(3, 22), 2)
    if trader.cum_earnings == 0:    updates["cum_earnings"]    = round(random.uniform(500, 90000), 2)
    if trader.cum_copiers == 0:     updates["cum_copiers"]     = random.randint(20, 2500)
    if trader.profit_share == 0:    updates["profit_share"]    = random.choice([10, 15, 20, 25, 30])

    if updates:
        for field, value in updates.items():
            setattr(trader, field, value)
        trader.save(update_fields=list(updates.keys()))
