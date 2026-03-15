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
            "balance", "invested_value", "profit", "roi",
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
        ("profit",  "Profit"),
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
# CopyTrade
# ─────────────────────────────────────────────────────────────────────────────

_FC = "form-control"

class CopyTradeForm(forms.ModelForm):
    class Meta:
        model  = CopyTrade
        fields = ["asset", "trade_type", "direction", "price", "pnl", "status", "category"]
        widgets = {
            "asset":      forms.TextInput(attrs={"class": _FC, "placeholder": "e.g. BTC/USD"}),
            "trade_type": forms.Select(attrs={"class": _FC}),
            "direction":  forms.Select(attrs={"class": _FC}),
            "price":      forms.NumberInput(attrs={"step": "0.01", "class": _FC}),
            "pnl":        forms.NumberInput(attrs={"step": "0.01", "class": _FC}),
            "status":     forms.Select(attrs={"class": _FC}),
            "category":   forms.Select(attrs={"class": _FC}),
        }


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


class BulkCopyTradeForm(forms.Form):
    asset      = forms.CharField(max_length=100, widget=forms.TextInput(attrs={"placeholder": "e.g. BTC/USD", "class": _FC}))
    trade_type = forms.ChoiceField(choices=[("Market", "Market"), ("Limit", "Limit")], widget=forms.Select(attrs={"class": _FC}))
    direction  = forms.ChoiceField(choices=[("Long", "Long"), ("Short", "Short")], widget=forms.Select(attrs={"class": _FC}))
    price      = forms.DecimalField(max_digits=18, decimal_places=2, min_value=0, widget=forms.NumberInput(attrs={"step": "0.01", "class": _FC}))
    pnl        = forms.DecimalField(max_digits=18, decimal_places=2, widget=forms.NumberInput(attrs={"step": "0.01", "class": _FC}))
    status     = forms.ChoiceField(choices=[("open", "Open"), ("closed", "Closed"), ("pending", "Pending")], widget=forms.Select(attrs={"class": _FC}))
    category   = forms.ChoiceField(choices=[("stocks", "Stocks"), ("forex", "Forex"), ("commodities", "Commodities"), ("crypto", "Crypto")], widget=forms.Select(attrs={"class": _FC}))
