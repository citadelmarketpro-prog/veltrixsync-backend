from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import (
    AdminWallet,
    CopyRelationship,
    CopyTrade,
    Notification,
    PortfolioAllocation,
    Trader,
    TradeHistory,
    TraderAsset,
    TraderPosition,
    TraderSection,
    Transaction,
)

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password  = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    class Meta:
        model  = User
        fields = ["id", "username", "email", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )
        return user


class LoginSerializer(serializers.Serializer):
    email    = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class UserProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "avatar_url", "bio",
            "balance", "invested_value", "profit", "roi",
            "kyc_status",
            "date_joined",
        ]
        read_only_fields = [
            "id", "email", "balance", "invested_value", "profit", "roi",
            "kyc_status", "date_joined",
        ]

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class UpdateProfileSerializer(serializers.ModelSerializer):
    # Explicitly declare as ImageField so DRF passes the uploaded file
    # object to the CloudinaryField backend (same pattern as KycSerializer).
    avatar = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = User
        fields = ["username", "first_name", "last_name", "bio", "avatar"]


class KycSerializer(serializers.ModelSerializer):
    """Read + submit KYC data. File fields (id_front/id_back) handled via multipart."""
    id_front_url = serializers.SerializerMethodField(read_only=True)
    id_back_url  = serializers.SerializerMethodField(read_only=True)

    # CloudinaryField extends CharField, so DRF would treat uploads as strings.
    # Explicitly declare as ImageField so DRF validates and passes the file object
    # to the model, which Cloudinary storage then picks up on save().
    id_front = serializers.ImageField(required=False, allow_null=True)
    id_back  = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model  = User
        fields = [
            # personal (first_name/last_name live on AbstractUser)
            "first_name", "last_name", "title", "date_of_birth", "phone",
            # address
            "street_address", "city", "province", "zipcode",
            # identity
            "id_type", "id_front", "id_back", "id_front_url", "id_back_url",
            # financial
            "currency", "employment_status", "income_source",
            "industry", "education_level", "annual_income", "net_worth",
            # status (read-only to user)
            "kyc_status", "kyc_submitted_at", "kyc_reject_reason",
        ]
        read_only_fields = ["kyc_status", "kyc_submitted_at", "kyc_reject_reason"]

    def get_id_front_url(self, obj):
        if obj.id_front:
            return obj.id_front.url  # Cloudinary returns absolute URL directly
        return None

    def get_id_back_url(self, obj):
        if obj.id_back:
            return obj.id_back.url  # Cloudinary returns absolute URL directly
        return None


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        # Always return without revealing whether the email exists (prevents enumeration)
        return value.lower()


class ResetPasswordSerializer(serializers.Serializer):
    uid      = serializers.CharField()
    token    = serializers.CharField()
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label="Confirm password")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    password     = serializers.CharField(write_only=True, validators=[validate_password])
    password2    = serializers.CharField(write_only=True, label="Confirm new password")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Notification
        fields = ["id", "notif_type", "title", "body", "is_read", "created_at"]
        read_only_fields = ["id", "notif_type", "title", "body", "created_at"]


# ─────────────────────────────────────────────────────────────────────────────
# Trader serializers
# ─────────────────────────────────────────────────────────────────────────────

_RISK_DISPLAY = {
    "high":     "High Risk",
    "moderate": "Moderate Risk",
    "balanced": "Balanced Risk",
    "low":      "Low Risk",
    "safe":     "Safe",
}

_CATEGORY_DISPLAY = {
    "crypto":             "Crypto",
    "stocks":             "Stocks",
    "healthcare":         "Healthcare",
    "financial_services": "Financial Services",
    "options":            "Options",
    "tech":               "Tech",
    "etf":                "ETF",
    "manufacturing":      "Manufacturing",
}


class TraderSerializer(serializers.ModelSerializer):
    """Flat trader representation used in all list sections."""
    initials   = serializers.SerializerMethodField()
    role       = serializers.CharField(source="specialty")
    desc       = serializers.CharField(source="bio")
    profit     = serializers.SerializerMethodField()
    copiers    = serializers.IntegerField(source="copiers_count")
    color      = serializers.CharField(source="avatar_color")
    tags       = serializers.SerializerMethodField()
    risk       = serializers.SerializerMethodField()
    rank       = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()

    class Meta:
        model  = Trader
        fields = [
            "id", "name", "role", "specialty", "desc", "avatar_url",
            "color", "initials", "tags", "profit", "copiers", "risk",
            "rank", "market_category", "min_capital", "roi", "win_rate",
            "trading_days", "followers_count",
        ]

    def get_initials(self, obj):
        parts = obj.name.split()
        return "".join(p[0] for p in parts[:2]).upper()

    def get_profit(self, obj):
        sign = "+" if obj.roi >= 0 else ""
        return f"{sign}{obj.roi:.2f}%"

    def get_tags(self, obj):
        return list(obj.trader_tags.values_list("name", flat=True))

    def get_risk(self, obj):
        return _RISK_DISPLAY.get(obj.risk_level, "")

    def get_rank(self, obj):
        return getattr(obj, "_section_rank", None)

    def get_avatar_url(self, obj):
        if obj.avatar:
            return obj.avatar.url
        return None


class TraderAssetSerializer(serializers.ModelSerializer):
    avg_return   = serializers.SerializerMethodField()
    avg_risk     = serializers.SerializerMethodField()
    success_rate = serializers.SerializerMethodField()
    icon_url     = serializers.SerializerMethodField()

    class Meta:
        model  = TraderAsset
        fields = ["icon_url", "name", "ticker", "avg_return", "avg_risk", "risk_label", "success_rate"]

    def get_icon_url(self, obj):
        if obj.icon:
            return obj.icon.url
        return None

    def get_avg_return(self, obj):
        return f"+{obj.avg_return:.2f}%" if obj.avg_return >= 0 else f"{obj.avg_return:.2f}%"

    def get_avg_risk(self, obj):
        return f"{obj.avg_risk:.2f}%"

    def get_success_rate(self, obj):
        return f"{obj.success_rate:.2f}%"


class PortfolioAllocationSerializer(serializers.ModelSerializer):
    pct = serializers.FloatField()

    class Meta:
        model  = PortfolioAllocation
        fields = ["label", "pct", "color"]


class TraderPositionSerializer(serializers.ModelSerializer):
    invested  = serializers.SerializerMethodField()
    pl        = serializers.SerializerMethodField()
    plPositive = serializers.SerializerMethodField()
    value     = serializers.SerializerMethodField()
    sell      = serializers.SerializerMethodField()
    buy       = serializers.SerializerMethodField()
    date      = serializers.DateTimeField(source="opened_at")

    class Meta:
        model  = TraderPosition
        fields = ["market", "date", "direction", "invested", "pl", "plPositive", "value", "sell", "buy"]

    def get_invested(self, obj):   return f"{obj.invested:.2f}%"
    def get_value(self, obj):      return f"{obj.value:.2f}%"
    def get_sell(self, obj):       return f"{obj.sell_price:.2f}"
    def get_buy(self, obj):        return f"{obj.buy_price:.2f}"
    def get_plPositive(self, obj): return obj.pl >= 0
    def get_pl(self, obj):
        sign = "+" if obj.pl >= 0 else ""
        return f"{sign}{obj.pl:.2f}%"


class TradeHistorySerializer(serializers.ModelSerializer):
    plPositive = serializers.SerializerMethodField()
    pl         = serializers.SerializerMethodField()
    open       = serializers.SerializerMethodField()
    close      = serializers.SerializerMethodField()
    openDate   = serializers.DateTimeField(source="open_date")
    closeDate  = serializers.DateTimeField(source="close_date")
    orderType  = serializers.CharField(source="order_type")
    date       = serializers.DateTimeField(source="close_date")

    class Meta:
        model  = TradeHistory
        fields = ["name", "date", "orderType", "position", "open", "openDate", "close", "closeDate", "pl", "plPositive"]

    def get_plPositive(self, obj): return obj.pl >= 0
    def get_pl(self, obj):
        sign = "+" if obj.pl >= 0 else ""
        return f"{sign}{obj.pl:.2f}%"
    def get_open(self, obj):  return f"{obj.open_price:.0f}"
    def get_close(self, obj): return f"{obj.close_price:.0f}"


class CopyRelationshipSerializer(serializers.ModelSerializer):
    name     = serializers.SerializerMethodField()
    date     = serializers.DateTimeField(source="started_at")
    copyDays = serializers.SerializerMethodField()
    assets   = serializers.SerializerMethodField()
    pl       = serializers.SerializerMethodField()

    class Meta:
        model  = CopyRelationship
        fields = ["name", "date", "copyDays", "assets", "pl"]

    def get_name(self, obj):
        u = obj.copier
        full = f"{u.first_name} {u.last_name}".strip()
        return full or u.username

    def get_copyDays(self, obj):
        from django.utils import timezone
        return (timezone.now() - obj.started_at).days

    def get_assets(self, obj):
        return f"{obj.allocated_amount:,.0f}"

    def get_pl(self, obj):
        sign = "+" if obj.pl >= 0 else ""
        return f"{sign}{obj.pl:,.1f}"


class TraderDetailSerializer(TraderSerializer):
    """Full trader profile for the detail page — extends TraderSerializer."""
    roi_display           = serializers.SerializerMethodField()
    masterPnl             = serializers.SerializerMethodField()
    accountAssets         = serializers.SerializerMethodField()
    maxDrawdown           = serializers.SerializerMethodField()
    riskDisplay           = serializers.SerializerMethodField()
    cumEarnings           = serializers.SerializerMethodField()
    cumCopiers            = serializers.SerializerMethodField()
    profitShare           = serializers.SerializerMethodField()
    winRate               = serializers.SerializerMethodField()
    minCapitalDisplay     = serializers.SerializerMethodField()
    is_copying            = serializers.SerializerMethodField()
    copy_status           = serializers.SerializerMethodField()
    top_assets            = TraderAssetSerializer(source="trader_assets", many=True, read_only=True)
    portfolio_allocations = PortfolioAllocationSerializer(many=True, read_only=True)

    class Meta(TraderSerializer.Meta):
        fields = TraderSerializer.Meta.fields + [
            "roi_display", "masterPnl", "accountAssets", "maxDrawdown",
            "riskDisplay", "cumEarnings", "cumCopiers", "profitShare", "winRate",
            "minCapitalDisplay", "followers_count", "trading_days",
            "top_assets", "portfolio_allocations", "is_copying", "copy_status",
        ]

    def get_roi_display(self, obj):
        sign = "+" if obj.roi >= 0 else ""
        return f"{sign}{obj.roi:.2f}%"

    def get_masterPnl(self, obj):
        sign = "+" if obj.master_pnl >= 0 else "-"
        return f"{sign}${abs(obj.master_pnl):,.2f}"

    def get_accountAssets(self, obj):
        return f"${obj.account_assets:,.2f}"

    def get_maxDrawdown(self, obj):
        return f"{obj.max_drawdown:.2f}%"

    def get_riskDisplay(self, obj):
        return _RISK_DISPLAY.get(obj.risk_level, "")

    def get_cumEarnings(self, obj):
        sign = "+" if obj.cum_earnings >= 0 else "-"
        return f"{sign}${abs(obj.cum_earnings):,.2f}"

    def get_cumCopiers(self, obj):
        return f"{obj.cum_copiers:,}"

    def get_profitShare(self, obj):
        return f"{obj.profit_share:.0f}%"

    def get_winRate(self, obj):
        return f"{obj.win_rate:.2f}%"

    def get_minCapitalDisplay(self, obj):
        return f"${obj.min_capital:,.2f}"

    def get_is_copying(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        rel = CopyRelationship.objects.filter(copier=request.user, trader=obj).first()
        return rel.status == "active" if rel else False

    def get_copy_status(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        rel = CopyRelationship.objects.filter(copier=request.user, trader=obj).first()
        return rel.status if rel else None


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────

class TransactionSerializer(serializers.ModelSerializer):
    tx_type    = serializers.CharField(source="get_tx_type_display")   # "Deposit" / "Withdrawal"
    status     = serializers.CharField(source="get_status_display")    # "Pending" / "Completed" / "Rejected"
    date       = serializers.DateTimeField(source="created_at")        # ISO-8601, frontend formats
    units      = serializers.SerializerMethodField()
    amount_usd = serializers.SerializerMethodField()
    tx_id      = serializers.UUIDField()

    class Meta:
        model  = Transaction
        fields = ["id", "date", "tx_type", "asset", "units", "amount_usd", "status", "tx_id"]

    def get_units(self, obj):
        return f"{obj.units:.8f}"

    def get_amount_usd(self, obj):
        return f"${obj.amount_usd:,.2f}"


# ─────────────────────────────────────────────────────────────────────────────
# AdminWallet
# ─────────────────────────────────────────────────────────────────────────────

class AdminWalletSerializer(serializers.ModelSerializer):
    name_display = serializers.CharField(source="get_name_display", read_only=True)
    icon_url     = serializers.SerializerMethodField()

    class Meta:
        model  = AdminWallet
        fields = ["id", "name", "name_display", "symbol", "network", "address", "icon_url"]

    def get_icon_url(self, obj):
        if obj.icon:
            return obj.icon.url
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Deposit / Withdrawal request
# ─────────────────────────────────────────────────────────────────────────────

class DepositSerializer(serializers.Serializer):
    wallet_id  = serializers.IntegerField()
    amount_usd = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))

    def validate_wallet_id(self, value):
        if not AdminWallet.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive wallet.")
        return value


class WithdrawalSerializer(serializers.Serializer):
    WITHDRAW_FROM_CHOICES = ["balance", "profit"]

    wallet_id      = serializers.IntegerField()
    amount_usd     = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    wallet_address = serializers.CharField(max_length=500)
    withdraw_from  = serializers.ChoiceField(choices=WITHDRAW_FROM_CHOICES)

    def validate_wallet_id(self, value):
        if not AdminWallet.objects.filter(pk=value, is_active=True).exists():
            raise serializers.ValidationError("Invalid or inactive wallet.")
        return value


# ─────────────────────────────────────────────────────────────────────────────
# CopyTrade
# ─────────────────────────────────────────────────────────────────────────────

class CopyTradeSerializer(serializers.ModelSerializer):
    trader_name  = serializers.CharField(source="trader.name", read_only=True)
    trader_id    = serializers.IntegerField(source="trader.id", read_only=True)
    pnl_positive = serializers.SerializerMethodField()
    pnl_display  = serializers.SerializerMethodField()

    class Meta:
        model  = CopyTrade
        fields = [
            "id", "trader_id", "trader_name", "asset", "trade_type",
            "direction", "price", "pnl", "pnl_display", "pnl_positive",
            "status", "created_at",
        ]

    def get_pnl_positive(self, obj):
        return obj.pnl >= 0

    def get_pnl_display(self, obj):
        sign = "+" if obj.pnl >= 0 else ""
        return f"{sign}${abs(obj.pnl):,.2f}"


class CopyingTraderSerializer(serializers.ModelSerializer):
    """Lightweight serializer for traders the user is actively copying."""
    trader_id    = serializers.IntegerField(source="trader.id")
    trader_name  = serializers.CharField(source="trader.name")
    avatar_url   = serializers.SerializerMethodField()
    avatar_color = serializers.CharField(source="trader.avatar_color")
    roi          = serializers.CharField(source="trader.roi")
    risk_level   = serializers.CharField(source="trader.risk_level")
    min_capital  = serializers.DecimalField(source="trader.min_capital", max_digits=18, decimal_places=2)

    class Meta:
        model  = CopyRelationship
        fields = [
            "id", "trader_id", "trader_name", "avatar_url", "avatar_color",
            "roi", "risk_level", "min_capital", "allocated_amount", "pl", "started_at",
        ]

    def get_avatar_url(self, obj):
        if obj.trader.avatar:
            return obj.trader.avatar.url
        return None
