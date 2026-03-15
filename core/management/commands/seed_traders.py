"""
python manage.py seed_traders
python manage.py seed_traders --clear

Creates Trader records from the frontend static data with full detail data
(assets, portfolio allocations, open positions, trade history, copiers).

Run in development only.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import (
    CopyRelationship,
    PortfolioAllocation,
    Trader,
    TradeHistory,
    TraderAsset,
    TraderPosition,
    TraderSection,
    TraderTag,
)

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Trader seed data — matches frontend static arrays exactly
# Each tuple:
#   (name, specialty, bio, color, risk_level, market_category,
#    roi, copiers_count, followers_count, min_capital, trading_days,
#    master_pnl, account_assets, max_drawdown, cum_earnings, cum_copiers,
#    profit_share, win_rate, tags, sections)
#
#   sections = list of (section_name, rank) tuples
# ─────────────────────────────────────────────────────────────────────────────

TRADERS = [
    # ── Trending Investors ────────────────────────────────────────────────────
    (
        "Jordan Blake", "Trading Strategist",
        "Since 2020, my portfolio has seen a growth of 32%. Join me to replicate my success on these markets.",
        "#4a7a6a", "balanced", "stocks",
        32.50, 740, 320, 50000, 1095,
        4230.50, 5250.75, 9.87, 312480.25, 11235, 12, 95.20,
        ["Forex", "Stocks"],
        [("trending", 1)],
    ),
    (
        "Linda Johnson", "Market Analyst",
        "My trading strategies have yielded a 21% increase since 2016. Let's trade together and grow.",
        "#8a7060", "low", "stocks",
        28.75, 490, 210, 30000, 2555,
        3100.00, 4200.00, 7.50, 245000.00, 8900, 10, 91.50,
        ["Market Analyst", "Forex"],
        [("trending", 2)],
    ),
    (
        "Carlos Mendoza", "Investment Analyst",
        "With a 30% portfolio growth since 2019, I'm ready to share my insights with you.",
        "#5a9fd4", "moderate", "crypto",
        29.05, 612, 280, 40000, 1460,
        3800.00, 4800.00, 11.20, 278000.00, 9500, 11, 88.70,
        ["Investment Analyst", "Cryptocurrency"],
        [("trending", 3)],
    ),
    (
        "Emma Lee", "Financial Trader",
        "My portfolio has yielded by 28%. Copy my trades and let's grow together.",
        "#c07858", "balanced", "stocks",
        30.15, 504, 230, 35000, 1825,
        3500.00, 4600.00, 8.90, 260000.00, 9100, 11, 92.30,
        ["Stocks", "Derivatives"],
        [("trending", 4)],
    ),
    (
        "Marcus Vael", "Quantitative Analyst",
        "Leverage my 9.8% average monthly return with data-driven strategies built over 5+ years.",
        "#7860a8", "moderate", "crypto",
        27.90, 381, 185, 25000, 1825,
        2900.00, 3900.00, 12.50, 198000.00, 7200, 10, 86.40,
        ["Quant", "Crypto"],
        [("trending", 5)],
    ),

    # ── Rising Stars ──────────────────────────────────────────────────────────
    (
        "Liam O'Connor", "Flow Specialist",
        "Specialising in order flow analysis to capture short-term momentum. Steady and growing.",
        "#6090c8", "moderate", "options",
        18.75, 320, 145, 15000, 365,
        1800.00, 2800.00, 14.30, 120000.00, 4500, 8, 82.10,
        [],
        [("rising_stars", 1)],
    ),
    (
        "Sofia Martinez", "Options Trading Guru",
        "High-conviction options plays with defined risk. Consistent alpha since I started.",
        "#d87060", "high", "options",
        22.10, 412, 190, 20000, 548,
        2200.00, 3200.00, 18.40, 158000.00, 5800, 12, 79.60,
        [],
        [("rising_stars", 2)],
    ),
    (
        "Ethan Zhang", "Commodity Trader",
        "Focused on commodities and macro trends. Low risk, steady compounding.",
        "#58a878", "low", "stocks",
        15.50, 210, 98, 10000, 730,
        1400.00, 2200.00, 6.10, 85000.00, 3200, 7, 89.30,
        [],
        [("rising_stars", 3)],
    ),
    (
        "Nia Thompson", "Derivatives Expert",
        "Using derivatives to build consistent, safe returns. Preservation of capital first.",
        "#8860b8", "safe", "options",
        20.85, 310, 140, 18000, 456,
        2000.00, 3000.00, 5.80, 135000.00, 5000, 9, 93.70,
        [],
        [("rising_stars", 4)],
    ),
    (
        "Aiden Park", "Momentum Trader",
        "Riding breakouts and momentum plays across tech and growth equities.",
        "#e8a060", "moderate", "stocks",
        19.40, 278, 128, 12000, 420,
        1900.00, 2700.00, 13.20, 105000.00, 3900, 9, 84.50,
        [],
        [("rising_stars", 5)],
    ),

    # ── Most Copied by Categories ─────────────────────────────────────────────
    (
        "Evelyn Dubois", "Options Trading",
        "Top-ranked options trader with consistent alpha generation through disciplined setups.",
        "#e8a060", "high", "options",
        32.53, 789, 360, 55000, 1642,
        4500.00, 5800.00, 10.20, 342000.00, 12500, 13, 94.10,
        [],
        [("most_copied", 1)],
    ),
    (
        "Mateo Vargas", "Day Trading",
        "Full-time day trader specialising in high-probability setups. Consistency is my edge.",
        "#6090c8", "moderate", "stocks",
        28.79, 634, 298, 45000, 1460,
        3800.00, 4900.00, 9.50, 285000.00, 10400, 11, 90.80,
        [],
        [("most_copied", 2)],
    ),
    (
        "Aaliyah Ramirez", "Value Investing",
        "Patient value investor. I find mispriced assets and let compounding do the rest.",
        "#d87060", "low", "stocks",
        26.19, 592, 275, 40000, 2190,
        3200.00, 4300.00, 7.30, 255000.00, 9300, 10, 91.20,
        [],
        [("most_copied", 3)],
    ),
    (
        "Jamieson Patel", "Swing Trading",
        "Swing trading major indices and blue chips. Risk management is paramount.",
        "#58a878", "low", "stocks",
        25.64, 578, 268, 38000, 1825,
        3100.00, 4100.00, 8.10, 248000.00, 9000, 10, 90.10,
        [],
        [("most_copied", 4)],
    ),
    (
        "Scarlett Nguyen", "Algorithmic Trading",
        "Systematic algo strategies running 24/7. Data-driven, emotion-free.",
        "#8860b8", "moderate", "tech",
        25.22, 562, 260, 36000, 1460,
        3000.00, 4000.00, 9.80, 238000.00, 8700, 11, 89.60,
        [],
        [("most_copied", 5)],
    ),
    (
        "Kellan O'Connell", "Forex Trading",
        "Major and minor forex pairs. Technically driven with strict risk rules.",
        "#4a7a6a", "low", "stocks",
        24.91, 555, 255, 34000, 1825,
        2900.00, 3900.00, 7.60, 230000.00, 8500, 10, 88.90,
        [],
        [("most_copied", 6)],
    ),
    (
        "Zoya Rhodes", "Commodities Trading",
        "Gold, oil, and agricultural commodities. Hedging macro risks with precision.",
        "#c07858", "moderate", "stocks",
        24.67, 548, 252, 32000, 1642,
        2800.00, 3800.00, 10.40, 225000.00, 8200, 11, 87.30,
        [],
        [("most_copied", 7)],
    ),
    (
        "Kael Kline", "Social Trading",
        "Combining crowd intelligence with technical analysis for superior returns.",
        "#5a9fd4", "moderate", "stocks",
        24.35, 539, 248, 30000, 1095,
        2700.00, 3700.00, 11.20, 218000.00, 8000, 10, 86.80,
        [],
        [("most_copied", 8)],
    ),
    (
        "Jaslyn Kaiser", "Event-Driven Investing",
        "Capturing alpha through earnings, M&A, and macro events. Disciplined sizing.",
        "#e8c040", "low", "stocks",
        24.02, 530, 244, 28000, 1825,
        2600.00, 3600.00, 8.90, 210000.00, 7700, 10, 88.10,
        [],
        [("most_copied", 9)],
    ),
    (
        "Braden Acosta", "Quantitative Analysis",
        "Pure quant. Every trade is backed by statistical models and rigorous back-testing.",
        "#8a7060", "moderate", "tech",
        23.88, 526, 240, 26000, 1460,
        2500.00, 3500.00, 12.10, 205000.00, 7500, 11, 85.70,
        [],
        [("most_copied", 10)],
    ),

    # ── Reliable Traders ──────────────────────────────────────────────────────
    (
        "Elias Rossi", "Risk Management Specialist",
        "My priority is capital preservation. Steady returns with minimal drawdowns.",
        "#6090c8", "balanced", "stocks",
        15.23, 342, 158, 20000, 1460,
        1500.00, 2500.00, 6.40, 112000.00, 4100, 8, 90.50,
        [],
        [("reliable", 1)],
    ),
    (
        "Naomi Walker", "Portfolio Manager",
        "Diversified, well-researched portfolio management. Low risk, consistent growth.",
        "#8a7060", "low", "stocks",
        18.92, 412, 190, 25000, 1825,
        1900.00, 2900.00, 5.20, 148000.00, 5400, 8, 92.80,
        [],
        [("reliable", 2)],
    ),
    (
        "Damian Green", "Investment Strategist",
        "Long-only, quality growth stocks. Patient approach delivering real returns.",
        "#58a878", "low", "stocks",
        12.55, 289, 132, 15000, 2190,
        1200.00, 2000.00, 4.80, 88000.00, 3200, 7, 91.30,
        [],
        [("reliable", 3)],
    ),
    (
        "Isabelle Flores", "Global Macro Investor",
        "Top-down macro approach across FX, rates, and equities. Balanced risk profile.",
        "#d87060", "balanced", "stocks",
        16.47, 380, 175, 22000, 1642,
        1600.00, 2600.00, 7.90, 125000.00, 4600, 9, 89.70,
        [],
        [("reliable", 4)],
    ),
    (
        "Omar Fayed", "Fixed Income Analyst",
        "Bond and fixed income specialist. Safety first, with a focus on real yield.",
        "#4a7a6a", "low", "financial_services",
        14.10, 265, 120, 18000, 1825,
        1300.00, 2200.00, 4.10, 98000.00, 3600, 7, 93.10,
        [],
        [("reliable", 5)],
    ),

    # ── Proven Stability ──────────────────────────────────────────────────────
    (
        "Julian Hayes", "Quantitative Analyst",
        "Quant strategies with a focus on long-term risk-adjusted returns.",
        "#4a7a6a", "low", "tech",
        22.51, 497, 228, 30000, 2190,
        2400.00, 3400.00, 6.70, 195000.00, 7100, 10, 90.20,
        ["Quant Trader", "FinTech"],
        [("proven", 1)],
    ),
    (
        "Aurora Chen", "Options Trader",
        "Options expert with a track record of consistent alpha and controlled risk.",
        "#e8c040", "moderate", "options",
        25.84, 584, 268, 38000, 1825,
        2900.00, 3900.00, 8.30, 228000.00, 8300, 11, 91.60,
        ["Options Expert", "Derivatives"],
        [("proven", 2)],
    ),
    (
        "Declan Ward", "Algorithmic Trader",
        "Algo and AI-driven strategies. Fully systematic, fully transparent.",
        "#5a9fd4", "balanced", "tech",
        21.39, 465, 214, 28000, 1642,
        2200.00, 3200.00, 9.40, 178000.00, 6500, 10, 88.30,
        ["Algo Trading", "AI Trading"],
        [("proven", 3)],
    ),
    (
        "Anya Petrova", "Value Investor",
        "Deep value, long-term investor. I buy great businesses at fair prices.",
        "#8860b8", "low", "stocks",
        19.76, 420, 192, 25000, 2555,
        2000.00, 3000.00, 5.60, 158000.00, 5800, 9, 92.50,
        ["Value Investing", "Long-Term Value"],
        [("proven", 4)],
    ),
    (
        "Felix Andrade", "Multi-Asset Trader",
        "Cross-asset portfolio spanning equities, commodities, and macro plays.",
        "#c07858", "moderate", "stocks",
        23.05, 511, 234, 32000, 1825,
        2500.00, 3500.00, 10.80, 198000.00, 7200, 10, 87.90,
        ["Macro", "Equities"],
        [("proven", 5)],
    ),

    # ── Detail page hero trader ───────────────────────────────────────────────
    (
        "Elias Nunez", "Risk Management Expert",
        "Hi, I'm Elias! My portfolio has grown by 35% this year. Start copying my trades today!",
        "#6090c8", "low", "stocks",
        35.12, 789, 342, 138696, 612,
        4230.50, 5250.75, 9.87, 312480.25, 11235, 12, 95.20,
        ["Risk guru", "Indices", "Options guru", "Leverage Expert", "Volatility Guru"],
        [],  # no section — appears via similar traders
    ),
]

# ─────────────────────────────────────────────────────────────────────────────
# Template detail data applied to every trader (varied by ROI multiplier)
# ─────────────────────────────────────────────────────────────────────────────

TEMPLATE_ASSETS = [
    ("AU",  "Gold",      "XAU", 21.45, -5.22, "Avg. Risk",  88.50),
    ("S&P", "S&P 500",   "SPX", 19.78, -4.89, "Avg. Risk",  92.70),
    ("€$",  "EUR/USD",   "EUR", 17.34, -6.15, "Avg. Risk",  89.10),
    ("",    "Apple",     "AAPL",20.55, -3.92, "Avg. Loss",  94.30),
    ("Ξ",   "Ethereum",  "ETH", 16.81, -7.29, "Avg. Risk",  81.70),
]

TEMPLATE_ALLOCATIONS = [
    ("Forex",   30, "#4a7a5a"),
    ("Stocks",  35, "#6aaa7a"),
    ("Indices", 35, "#b0d45a"),
]

TEMPLATE_POSITIONS = [
    ("Vanguard RTX Index",    "Short", 15.72, 42.18,  True,  38.59, 18.45, 21.36),
    ("iShares Robotics ETF",  "Short", 15.72, -11.57, False, 38.59, 18.45, 21.36),
    ("ARK Innovation Fund",   "Short", 15.72, 42.18,  True,  38.59, 18.45, 21.36),
    ("Global X Lithium ETF",  "Short", 15.72, -11.57, False, 38.59, 18.45, 21.36),
    ("VanEck Gold Miners ETF","Short", 15.72, -11.57, False, 38.59, 18.45, 21.36),
    ("iShares MSCI India",    "Long",  15.72, 28.44,  True,  38.59, 18.45, 21.36),
    ("ProShares Bitcoin ETF", "Long",  15.72, -8.30,  False, 38.59, 18.45, 21.36),
]

TEMPLATE_HISTORY = [
    ("ETH/USD", "Limit",  "Open Short", 970,   965,   2.87,  True),
    ("ETH/USD", "Market", "Open Long",  155,   167,   4.32,  True),
    ("ETH/USD", "Limit",  "Open Short", 320,   342,   6.78,  True),
    ("ETH/USD", "Market", "Open Long",  870,   899,   1.56,  True),
    ("ETH/USD", "Limit",  "Open Short", 450,   420,   7.89,  True),
    ("ETH/USD", "Market", "Open Long",  1240,  1310,  5.65,  True),
    ("ETH/USD", "Limit",  "Open Short", 680,   654,  -3.82, False),
]

COPIER_NAMES = [
    ("Jamison", "Brew"),
    ("Mike", "Stonewood"),
    ("Lana", "Rose"),
    ("Fredrick", "Albert"),
    ("Cecilia", "Ralph"),
    ("Dana", "Winters"),
    ("Oscar", "Flynn"),
]


class Command(BaseCommand):
    help = "Seed Trader records with full detail data from the frontend static data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all existing Trader records and related data before seeding.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            deleted, _ = Trader.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {deleted} trader record(s) and their related data."))
            User.objects.filter(email__endswith="@copiers.seed").delete()

        # ── Create copier template users ──────────────────────────────────────
        copier_users = []
        for first, last in COPIER_NAMES:
            email = f"{first.lower()}.{last.lower()}@copiers.seed"
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={
                    "username":   f"{first.lower()}_{last.lower()}",
                    "first_name": first,
                    "last_name":  last,
                },
            )
            copier_users.append(user)
        self.stdout.write(f"Copier users ready: {len(copier_users)}")

        # ── Create each trader ────────────────────────────────────────────────
        now = timezone.now()
        created_count = 0

        for (
            name, specialty, bio, color, risk_level, market_category,
            roi, copiers_count, followers_count, min_capital, trading_days,
            master_pnl, account_assets, max_drawdown, cum_earnings, cum_copiers,
            profit_share, win_rate,
            tag_names, sections,
        ) in TRADERS:
            trader, created = Trader.objects.get_or_create(
                name=name,
                defaults={
                    "specialty":       specialty,
                    "bio":             bio,
                    "avatar_color":    color,
                    "risk_level":      risk_level,
                    "market_category": market_category,
                    "roi":             Decimal(str(roi)),
                    "copiers_count":   copiers_count,
                    "followers_count": followers_count,
                    "min_capital":     Decimal(str(min_capital)),
                    "trading_days":    trading_days,
                    "master_pnl":      Decimal(str(master_pnl)),
                    "account_assets":  Decimal(str(account_assets)),
                    "max_drawdown":    Decimal(str(max_drawdown)),
                    "cum_earnings":    Decimal(str(cum_earnings)),
                    "cum_copiers":     cum_copiers,
                    "profit_share":    Decimal(str(profit_share)),
                    "win_rate":        Decimal(str(win_rate)),
                },
            )

            if not created:
                self.stdout.write(f"  skip  {name} (already exists)")
                continue

            # Tags
            for tag_name in tag_names:
                tag, _ = TraderTag.objects.get_or_create(name=tag_name)
                trader.trader_tags.add(tag)

            # Section memberships
            for section_name, rank in sections:
                TraderSection.objects.get_or_create(
                    trader=trader, section=section_name,
                    defaults={"rank": rank},
                )

            # Scale factor so detail data varies slightly per trader
            scale = Decimal(str(roi)) / Decimal("25")

            # Assets
            for order, (icon, aname, ticker, avg_ret, avg_risk, risk_label, success) in enumerate(TEMPLATE_ASSETS):
                TraderAsset.objects.create(
                    trader=trader, icon=icon, name=aname, ticker=ticker,
                    avg_return=Decimal(str(round(avg_ret * float(scale), 2))),
                    avg_risk=Decimal(str(round(avg_risk * float(scale), 2))),
                    risk_label=risk_label,
                    success_rate=Decimal(str(min(99.99, round(success * float(scale), 2)))),
                    order=order,
                )

            # Portfolio allocations
            for order, (label, pct, col) in enumerate(TEMPLATE_ALLOCATIONS):
                PortfolioAllocation.objects.create(
                    trader=trader, label=label, pct=Decimal(str(pct)), color=col, order=order,
                )

            # Open positions
            for market, direction, invested, pl, pl_pos, value, sell, buy in TEMPLATE_POSITIONS:
                adj_pl = Decimal(str(round(pl * float(scale), 2)))
                TraderPosition.objects.create(
                    trader=trader, market=market, direction=direction,
                    invested=Decimal(str(invested)),
                    pl=adj_pl,
                    value=Decimal(str(value)),
                    sell_price=Decimal(str(sell)),
                    buy_price=Decimal(str(buy)),
                    opened_at=now - timedelta(days=10),
                )

            # Trade history
            for i, (hname, order_type, position, open_p, close_p, pl, pl_pos) in enumerate(TEMPLATE_HISTORY):
                adj_pl = Decimal(str(round(pl * float(scale), 2)))
                entry = now - timedelta(days=30 + i * 5)
                TradeHistory.objects.create(
                    trader=trader, name=hname,
                    order_type=order_type, position=position,
                    open_price=Decimal(str(open_p)),
                    open_date=entry,
                    close_price=Decimal(str(close_p)),
                    close_date=entry + timedelta(days=1),
                    pl=adj_pl,
                )

            # Copy relationships
            for idx, copier in enumerate(copier_users):
                days = 213 - idx * 8
                alloc = Decimal("200435") - Decimal(str(idx * 3000))
                pl_val = Decimal("345864") - Decimal(str(idx * 5000))
                CopyRelationship.objects.get_or_create(
                    copier=copier, trader=trader,
                    defaults={
                        "started_at":       now - timedelta(days=days),
                        "allocated_amount": alloc,
                        "pl":               pl_val,
                    },
                )

            self.stdout.write(self.style.SUCCESS(f"  created  {name} ({specialty})"))
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone. {created_count} trader(s) created."))
