import uuid

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from cloudinary.models import CloudinaryField


class User(AbstractUser):
    """
    Extended user model for SignalSync.
    Username + email are both required and unique.
    """
    email = models.EmailField(unique=True)

    # Profile
    avatar = CloudinaryField("avatar", folder="avatars", null=True, blank=True)
    bio    = models.TextField(blank=True, default="")

    # Financials (stored in USD)
    balance        = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    invested_value = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    profit         = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    roi            = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    # ── KYC — Personal ───────────────────────────────────────────────────────
    title         = models.CharField(max_length=10,  blank=True, default="")
    date_of_birth = models.DateField(null=True, blank=True)
    phone         = models.CharField(max_length=30,  blank=True, default="")

    # ── KYC — Address ────────────────────────────────────────────────────────
    street_address = models.CharField(max_length=255, blank=True, default="")
    city           = models.CharField(max_length=100, blank=True, default="")
    province       = models.CharField(max_length=100, blank=True, default="")
    zipcode        = models.CharField(max_length=20,  blank=True, default="")

    # ── KYC — Identity documents ─────────────────────────────────────────────
    ID_TYPE_CHOICES = [
        ("passport",         "Passport"),
        ("national_id",      "National ID"),
        ("drivers_license",  "Driver's Licence"),
        ("residence_permit", "Residence Permit"),
    ]
    id_type  = models.CharField(max_length=30, choices=ID_TYPE_CHOICES, blank=True, default="")
    id_front = CloudinaryField("id_front", folder="kyc/id", null=True, blank=True)
    id_back  = CloudinaryField("id_back",  folder="kyc/id", null=True, blank=True)

    # ── KYC — Financial background ────────────────────────────────────────────
    currency          = models.CharField(max_length=10,  blank=True, default="")
    employment_status = models.CharField(max_length=60,  blank=True, default="")
    income_source     = models.CharField(max_length=100, blank=True, default="")
    industry          = models.CharField(max_length=100, blank=True, default="")
    education_level   = models.CharField(max_length=60,  blank=True, default="")
    annual_income     = models.CharField(max_length=60,  blank=True, default="")
    net_worth         = models.CharField(max_length=60,  blank=True, default="")

    # ── KYC — Status ─────────────────────────────────────────────────────────
    KYC_STATUS_CHOICES = [
        ("not_submitted", "Not submitted"),
        ("submitted",     "Submitted"),
        ("under_review",  "Under review"),
        ("approved",      "Approved"),
        ("rejected",      "Rejected"),
    ]
    kyc_status        = models.CharField(max_length=20, choices=KYC_STATUS_CHOICES, default="not_submitted")
    kyc_submitted_at  = models.DateTimeField(null=True, blank=True)
    kyc_reviewed_at   = models.DateTimeField(null=True, blank=True)
    kyc_reject_reason = models.TextField(blank=True, default="")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


# ─────────────────────────────────────────────────────────────────────────────
# Notification
# ─────────────────────────────────────────────────────────────────────────────

class Notification(models.Model):
    TYPE_CHOICES = [
        ("trade",  "Trade"),
        ("wallet", "Wallet"),
        ("news",   "News"),
        ("kyc",    "KYC"),
        ("system", "System"),
    ]

    user       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    notif_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    title      = models.CharField(max_length=255)
    body       = models.TextField(blank=True, default="")
    is_read    = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.title}"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Tags
# ─────────────────────────────────────────────────────────────────────────────

class TraderTag(models.Model):
    name = models.CharField(max_length=60, unique=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# Trader — standalone profile (independent of User accounts)
# ─────────────────────────────────────────────────────────────────────────────

class Trader(models.Model):
    RISK_LEVEL_CHOICES = [
        ("high",     "High Risk"),
        ("moderate", "Moderate Risk"),
        ("balanced", "Balanced Risk"),
        ("low",      "Low Risk"),
        ("safe",     "Safe"),
    ]
    MARKET_CATEGORY_CHOICES = [
        ("crypto",             "Crypto"),
        ("stocks",             "Stocks"),
        ("healthcare",         "Healthcare"),
        ("financial_services", "Financial Services"),
        ("options",            "Options"),
        ("tech",               "Tech"),
        ("etf",                "ETF"),
        ("manufacturing",      "Manufacturing"),
    ]

    # Identity
    name         = models.CharField(max_length=200)
    bio          = models.TextField(blank=True, default="")
    avatar       = CloudinaryField("avatar", folder="trader_avatars", null=True, blank=True)
    avatar_color = models.CharField(max_length=20, blank=True, default="#4a7a6a")
    specialty    = models.CharField(max_length=120, blank=True, default="")

    # List-page stats
    roi             = models.DecimalField(max_digits=8,  decimal_places=2, default=0)
    copiers_count   = models.PositiveIntegerField(default=0)
    followers_count = models.PositiveIntegerField(default=0)
    min_capital     = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    trading_days    = models.PositiveIntegerField(default=0)
    win_rate        = models.DecimalField(max_digits=5,  decimal_places=2, default=0)

    # Categorisation
    risk_level      = models.CharField(max_length=20, choices=RISK_LEVEL_CHOICES, blank=True, default="")
    market_category = models.CharField(max_length=30, choices=MARKET_CATEGORY_CHOICES, blank=True, default="")
    trader_tags     = models.ManyToManyField("TraderTag", blank=True, related_name="traders")

    # Detail-page stats
    master_pnl     = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    account_assets = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    max_drawdown   = models.DecimalField(max_digits=8,  decimal_places=2, default=0)
    cum_earnings   = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    cum_copiers    = models.PositiveIntegerField(default=0)
    profit_share   = models.DecimalField(max_digits=5,  decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Section membership
# ─────────────────────────────────────────────────────────────────────────────

class TraderSection(models.Model):
    SECTION_CHOICES = [
        ("trending",     "Trending Investors"),
        ("rising_stars", "Rising Stars"),
        ("most_copied",  "Most Copied by Categories"),
        ("reliable",     "Reliable Traders"),
        ("proven",       "Proven Stability"),
    ]
    trader  = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="section_memberships")
    section = models.CharField(max_length=20, choices=SECTION_CHOICES)
    rank    = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = [("trader", "section")]
        ordering        = ["section", "rank"]

    def __str__(self):
        return f"{self.trader} — {self.get_section_display()} #{self.rank}"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Top assets (detail page)
# ─────────────────────────────────────────────────────────────────────────────

class TraderAsset(models.Model):
    trader       = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="trader_assets")
    icon         = CloudinaryField("icon", folder="asset_icons", null=True, blank=True)
    name         = models.CharField(max_length=100)
    ticker       = models.CharField(max_length=20, blank=True, default="")
    avg_return   = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    avg_risk     = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    risk_label   = models.CharField(max_length=50, blank=True, default="Avg. Risk")
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    order        = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.trader} / {self.name}"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Portfolio allocation (detail page)
# ─────────────────────────────────────────────────────────────────────────────

class PortfolioAllocation(models.Model):
    trader = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="portfolio_allocations")
    label  = models.CharField(max_length=60)
    pct    = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    color  = models.CharField(max_length=20, blank=True, default="")
    order  = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.trader} / {self.label} {self.pct}%"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Open positions (portfolio tab)
# ─────────────────────────────────────────────────────────────────────────────

class TraderPosition(models.Model):
    DIRECTION_CHOICES = [("Long", "Long"), ("Short", "Short")]

    trader     = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="positions")
    market     = models.CharField(max_length=150)
    direction  = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    invested   = models.DecimalField(max_digits=8,  decimal_places=2, default=0)
    pl         = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    value      = models.DecimalField(max_digits=8,  decimal_places=2, default=0)
    sell_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    buy_price  = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    opened_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-opened_at"]

    def __str__(self):
        return f"{self.trader} / {self.market} {self.direction}"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Trade history (history tab)
# ─────────────────────────────────────────────────────────────────────────────

class TradeHistory(models.Model):
    ORDER_TYPE_CHOICES = [("Market", "Market"), ("Limit", "Limit")]
    POSITION_CHOICES   = [
        ("Open Long",  "Open Long"),
        ("Open Short", "Open Short"),
        ("Closed",     "Closed"),
    ]

    trader      = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="trade_history")
    name        = models.CharField(max_length=150)
    order_type  = models.CharField(max_length=20, choices=ORDER_TYPE_CHOICES)
    position    = models.CharField(max_length=20, choices=POSITION_CHOICES)
    open_price  = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    open_date   = models.DateTimeField()
    close_price = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    close_date  = models.DateTimeField()
    pl          = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        ordering = ["-close_date"]

    def __str__(self):
        return f"{self.trader} / {self.name} {self.pl}%"


# ─────────────────────────────────────────────────────────────────────────────
# Trader — Copy relationship (copiers tab)
# copier = a regular User; trader = a Trader profile
# ─────────────────────────────────────────────────────────────────────────────

class CopyRelationship(models.Model):
    STATUS_CHOICES = [
        ("active",           "Active"),
        ("cancel_requested", "Cancel Requested"),
        ("cancelled",        "Cancelled"),
    ]

    copier           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="copying")
    trader           = models.ForeignKey("Trader", on_delete=models.CASCADE, related_name="copiers_rel")
    started_at       = models.DateTimeField(auto_now_add=True)
    allocated_amount = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    pl               = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status           = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    class Meta:
        unique_together = [("copier", "trader")]
        ordering        = ["-started_at"]

    def __str__(self):
        return f"{self.copier} copies {self.trader} [{self.status}]"


# ─────────────────────────────────────────────────────────────────────────────
# Copy Trade — individual trade injected by admin for a copy relationship
# ─────────────────────────────────────────────────────────────────────────────

class CopyTrade(models.Model):
    TRADE_TYPE_CHOICES = [("Market", "Market"), ("Limit", "Limit")]
    DIRECTION_CHOICES  = [("Long", "Long"), ("Short", "Short")]
    STATUS_CHOICES     = [("open", "Open"), ("closed", "Closed"), ("pending", "Pending")]
    CATEGORY_CHOICES   = [
        ("stocks",      "Stocks"),
        ("forex",       "Forex"),
        ("commodities", "Commodities"),
        ("crypto",      "Crypto"),
    ]

    copy_relationship = models.ForeignKey("CopyRelationship", on_delete=models.SET_NULL, null=True, blank=True, related_name="trades")
    user              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="copy_trades")
    trader            = models.ForeignKey("Trader", on_delete=models.SET_NULL, null=True, blank=True, related_name="investor_trades")
    asset             = models.CharField(max_length=100)
    trade_type        = models.CharField(max_length=20, choices=TRADE_TYPE_CHOICES, default="Market")
    direction         = models.CharField(max_length=10, choices=DIRECTION_CHOICES, default="Long")
    price             = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    pnl               = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status            = models.CharField(max_length=20, choices=STATUS_CHOICES, default="open")
    category          = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="stocks")
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} | {self.trader} | {self.asset} {self.direction}"


# ─────────────────────────────────────────────────────────────────────────────
# Transaction (deposit / withdrawal)
# ─────────────────────────────────────────────────────────────────────────────

class Transaction(models.Model):
    TX_TYPE_CHOICES = [
        ("deposit",    "Deposit"),
        ("withdrawal", "Withdrawal"),
    ]
    STATUS_CHOICES = [
        ("pending",   "Pending"),
        ("completed", "Completed"),
        ("rejected",  "Rejected"),
    ]

    user           = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="transactions")
    tx_type        = models.CharField(max_length=20, choices=TX_TYPE_CHOICES)
    asset          = models.CharField(max_length=20)
    units          = models.DecimalField(max_digits=28, decimal_places=8, default=0)
    amount_usd     = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    wallet_address = models.CharField(max_length=500, blank=True, default="")
    tx_id          = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} — {self.tx_type} {self.asset} ({self.status})"


# ─────────────────────────────────────────────────────────────────────────────
# AdminWallet — deposit addresses managed by the admin
# ─────────────────────────────────────────────────────────────────────────────

class AdminWallet(models.Model):
    WALLET_TYPE_CHOICES = [
        ("bitcoin",       "Bitcoin"),
        ("ethereum",      "Ethereum"),
        ("usdt_trc20",    "USDT (TRC20)"),
        ("usdt_erc20",    "USDT (ERC20)"),
        ("bnb",           "BNB (BEP20)"),
        ("usdc",          "USDC"),
        ("litecoin",      "Litecoin"),
        ("ripple",        "Ripple (XRP)"),
        ("solana",        "Solana"),
        ("dogecoin",      "Dogecoin"),
        ("tron",          "Tron (TRX)"),
        ("polygon",       "Polygon (MATIC)"),
        ("avalanche",     "Avalanche (AVAX)"),
        ("bitcoin_cash",  "Bitcoin Cash"),
    ]

    WALLET_DEFAULTS = {
        "bitcoin":       ("BTC",  "Bitcoin"),
        "ethereum":      ("ETH",  "ERC20"),
        "usdt_trc20":    ("USDT", "TRC20"),
        "usdt_erc20":    ("USDT", "ERC20"),
        "bnb":           ("BNB",  "BEP20"),
        "usdc":          ("USDC", "ERC20"),
        "litecoin":      ("LTC",  "Litecoin"),
        "ripple":        ("XRP",  "Ripple"),
        "solana":        ("SOL",  "Solana"),
        "dogecoin":      ("DOGE", "Dogecoin"),
        "tron":          ("TRX",  "TRC20"),
        "polygon":       ("MATIC","Polygon"),
        "avalanche":     ("AVAX", "C-Chain"),
        "bitcoin_cash":  ("BCH",  "Bitcoin Cash"),
    }

    name      = models.CharField(max_length=30, choices=WALLET_TYPE_CHOICES)
    symbol    = models.CharField(max_length=20)
    network   = models.CharField(max_length=100, blank=True, default="")
    address   = models.CharField(max_length=500)
    icon      = CloudinaryField("icon", folder="wallet_icons", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order     = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order", "name"]

    def save(self, *args, **kwargs):
        if self.name in self.WALLET_DEFAULTS:
            default_symbol, default_network = self.WALLET_DEFAULTS[self.name]
            if not self.symbol:
                self.symbol = default_symbol
            if not self.network:
                self.network = default_network
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_name_display()} — {self.address[:30]}…"
