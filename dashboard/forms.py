from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from core.models import (
    AdminWallet,
    CopyRelationship,
    CopyTrade,
    PortfolioAllocation,
    Trader,
    TraderAsset,
    TraderPosition,
    TradeHistory,
    TraderSection,
    TraderTag,
    Transaction,
)

User = get_user_model()


# ─────────────────────────────────────────────────────────────────────────────
# User
# ─────────────────────────────────────────────────────────────────────────────

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "username", "email",
            "balance", "roi", "percentage_roi",
            "kyc_status", "kyc_reject_reason",
            "is_active", "is_staff", "is_superuser",
        ]
        widgets = {
            "kyc_reject_reason": forms.Textarea(attrs={"rows": 3}),
        }


class UserCreateForm(forms.ModelForm):
    password  = forms.CharField(widget=forms.PasswordInput, validators=[validate_password])
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm password")

    class Meta:
        model  = User
        fields = ["first_name", "last_name", "username", "email", "is_staff", "is_superuser"]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password") != cleaned.get("password2"):
            raise forms.ValidationError({"password": "Passwords do not match."})
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user


class AdjustFundsForm(forms.Form):
    FIELD_CHOICES = [
        ("balance", "Main Balance"),
        ("roi",     "ROI (Profit)"),
    ]
    MODE_CHOICES = [
        ("add",      "Add"),
        ("subtract", "Subtract"),
        ("set",      "Set exact value"),
    ]
    field  = forms.ChoiceField(choices=FIELD_CHOICES)
    mode   = forms.ChoiceField(choices=MODE_CHOICES)
    amount = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0)
    note   = forms.CharField(required=False, max_length=255,
                             widget=forms.TextInput(attrs={"placeholder": "Internal note (optional)"}))


class RejectKycForm(forms.Form):
    reason = forms.CharField(
        label="Rejection reason",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Explain why KYC was rejected…"}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Trader
# ─────────────────────────────────────────────────────────────────────────────

class TraderForm(forms.ModelForm):
    trader_tags = forms.ModelMultipleChoiceField(
        queryset=TraderTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Tags",
    )

    class Meta:
        model = Trader
        fields = [
            "name", "bio", "avatar", "avatar_color", "specialty",
            "roi", "copiers_count", "followers_count", "min_capital",
            "trading_days", "win_rate", "risk_level", "market_category",
            "trader_tags",
            "master_pnl", "account_assets", "max_drawdown",
            "cum_earnings", "cum_copiers", "profit_share",
        ]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
        }


class TraderTagForm(forms.ModelForm):
    class Meta:
        model  = TraderTag
        fields = ["name"]


class TraderSectionForm(forms.ModelForm):
    class Meta:
        model  = TraderSection
        fields = ["section", "rank"]


class TraderAssetForm(forms.ModelForm):
    class Meta:
        model  = TraderAsset
        fields = ["icon", "name", "ticker", "avg_return", "avg_risk", "risk_label", "success_rate", "order"]


class PortfolioAllocationForm(forms.ModelForm):
    class Meta:
        model  = PortfolioAllocation
        fields = ["label", "pct", "color", "order"]


# ─────────────────────────────────────────────────────────────────────────────
# Transaction
# ─────────────────────────────────────────────────────────────────────────────

class TransactionEditForm(forms.ModelForm):
    class Meta:
        model  = Transaction
        fields = ["status", "asset", "units", "amount_usd", "wallet_address"]


class RejectTransactionForm(forms.Form):
    note = forms.CharField(
        required=False,
        label="Rejection note",
        widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Optional note…"}),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Wallet
# ─────────────────────────────────────────────────────────────────────────────

class AdminWalletForm(forms.ModelForm):
    class Meta:
        model  = AdminWallet
        fields = ["name", "symbol", "network", "address", "icon", "is_active", "order"]


# ─────────────────────────────────────────────────────────────────────────────
# CopyTrade — asset lists per type (used by form + JS in template)
# ─────────────────────────────────────────────────────────────────────────────

ASSET_MAP = {
    "stock": [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "JPM",
        "NFLX", "SPY", "QQQ", "BAC", "V", "AMD", "WMT", "DIS", "PYPL",
        "COIN", "SPX", "NDX", "BABA", "INTC", "GS", "MS", "UBER",
    ],
    "crypto": [
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "AVAX",
        "DOT", "MATIC", "LTC", "LINK", "UNI", "ATOM", "SHIB", "TRX",
        "FIL", "NEAR", "APT", "ARB",
    ],
    "forex": [
        "EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD",
        "USD/CAD", "NZD/USD", "EUR/GBP", "EUR/JPY", "GBP/JPY",
        "EUR/CHF", "AUD/JPY", "USD/MXN", "USD/ZAR",
    ],
}

_FC = "form-control"

# All valid asset values (flat set for server-side validation)
_ALL_ASSETS = {a for assets in ASSET_MAP.values() for a in assets}


class AddTradeForm(forms.Form):
    """Used for both single-investor and bulk trade injection."""
    TYPE_CHOICES = [("stock", "Stock"), ("crypto", "Crypto"), ("forex", "Forex")]
    DIRECTION_CHOICES = [("Buy", "Buy"), ("Sell", "Sell")]
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed"), ("pending", "Pending")]
    DURATION_CHOICES = [
        ("2m", "2 Minutes"), ("5m", "5 Minutes"), ("10m", "10 Minutes"),
        ("15m", "15 Minutes"), ("30m", "30 Minutes"), ("1h", "1 Hour"),
        ("2h", "2 Hours"), ("4h", "4 Hours"), ("6h", "6 Hours"),
        ("12h", "12 Hours"), ("1d", "1 Day"), ("3d", "3 Days"), ("1w", "1 Week"),
    ]

    asset_type   = forms.ChoiceField(choices=TYPE_CHOICES,      widget=forms.Select(attrs={"class": _FC, "id": "id_asset_type"}))
    asset        = forms.CharField(max_length=100,              widget=forms.Select(attrs={"class": _FC, "id": "id_asset"}))
    direction    = forms.ChoiceField(choices=DIRECTION_CHOICES, widget=forms.Select(attrs={"class": _FC}))
    entry        = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0,
                                      widget=forms.NumberInput(attrs={"step": "0.01", "class": _FC, "placeholder": "Entry price"}))
    earning_pct  = forms.DecimalField(max_digits=8, decimal_places=2,
                                      widget=forms.NumberInput(attrs={"step": "0.01", "class": _FC, "placeholder": "e.g. 4.5"}),
                                      label="Earning Percentage (%)")
    duration     = forms.ChoiceField(choices=DURATION_CHOICES, widget=forms.Select(attrs={"class": _FC}))
    status       = forms.ChoiceField(choices=STATUS_CHOICES,   widget=forms.Select(attrs={"class": _FC}))

    def clean_asset(self):
        asset = self.cleaned_data.get("asset", "").strip()
        if asset not in _ALL_ASSETS:
            raise forms.ValidationError("Invalid asset selection.")
        return asset


class TraderPositionForm(forms.ModelForm):
    class Meta:
        model  = TraderPosition
        fields = ["market", "direction", "invested", "pl", "value", "sell_price", "buy_price"]
        widgets = {
            "market": forms.TextInput(attrs={"placeholder": "e.g. BTC/USD"}),
        }


class TradeHistoryForm(forms.ModelForm):
    class Meta:
        model   = TradeHistory
        fields  = ["name", "order_type", "position", "open_price", "open_date", "close_price", "close_date", "pl"]
        widgets = {
            "open_date":  forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
            "close_date": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["open_date"].input_formats  = ["%Y-%m-%dT%H:%M"]
        self.fields["close_date"].input_formats = ["%Y-%m-%dT%H:%M"]


