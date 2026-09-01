import json
from django import forms
from django.utils.safestring import mark_safe
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from core.models import (
    AdminWallet,
    CopyRelationship,
    CopyTrade,
    DummyCopier,
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
    new_password = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Leave blank to keep current password", "autocomplete": "new-password"}),
        label="New Password (plain text)",
        help_text="If set, the password will be updated and stored in plain text for dev reference.",
    )

    class Meta:
        model = User
        fields = [
            # Account
            "first_name", "last_name", "username", "email",
            "bio",
            # Financials
            "balance", "roi", "percentage_roi",
            # KYC — Personal
            "title", "date_of_birth", "phone",
            # KYC — Address
            "street_address", "city", "province", "zipcode",
            # KYC — Identity
            "id_type",
            # KYC — Financial background
            "currency", "employment_status", "income_source",
            "industry", "education_level", "annual_income", "net_worth",
            # KYC — Status
            "kyc_status", "kyc_reject_reason",
            # Permissions
            "is_active", "is_staff", "is_superuser",
            "allow_transfer",
        ]
        widgets = {
            "bio":              forms.Textarea(attrs={"rows": 3}),
            "kyc_reject_reason": forms.Textarea(attrs={"rows": 3}),
            "date_of_birth":    forms.DateInput(attrs={"type": "date"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        plain = self.cleaned_data.get("new_password", "").strip()
        if plain:
            user.set_password(plain)
            user.password_plaintext = plain
        if commit:
            user.save()
        return user


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
        plain = self.cleaned_data["password"]
        user.set_password(plain)
        user.password_plaintext = plain
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
        widgets = {
            "color": forms.TextInput(attrs={"type": "color", "style": "height:42px; padding:4px;"}),
        }


# Inline formset — lets the trader edit page manage all Portfolio Allocation
# rows (add/edit/delete) in one submit, alongside the main trader fields.
#
# extra=0 is deliberate, not a typo: pct/order both have a non-empty model
# `default=0`, which Django's ModelForm machinery propagates onto the
# generated form field as `initial=0`. That makes has_changed() compare the
# untouched extra row's submitted "" against initial 0 (`0 != ""` -> True),
# so Django thinks the blank row was edited and fully validates it instead
# of skipping it — and it then fails on the genuinely-empty required fields
# (label, pct). With extra>0 this silently failed the WHOLE form (including
# unrelated fields like min_capital) on every edit, since the view only
# saves when both form.is_valid() and allocation_fs.is_valid() are True.
# The template's own "+ Add Allocation Row" button already renders new
# blank rows client-side (via the <template> + __prefix__ substitution), so
# extra=0 loses no functionality — it just stops baking pre-broken blank
# rows into every GET-rendered form.
PortfolioAllocationFormSet = forms.inlineformset_factory(
    Trader, PortfolioAllocation,
    form=PortfolioAllocationForm,
    fields=["label", "pct", "color", "order"],
    extra=0, can_delete=True,
)


class DummyCopierForm(forms.ModelForm):
    """Display-only 'Copiers' row shown on the public trader page — a free-text
    name, not linked to any real user account."""

    class Meta:
        model  = DummyCopier
        fields = ["name", "started_at", "allocated_amount", "pl"]
        widgets = {
            "started_at": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["started_at"].input_formats = ["%Y-%m-%dT%H:%M"]


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
# Custom / bulk client email
# ─────────────────────────────────────────────────────────────────────────────

class CustomEmailForm(forms.Form):
    """Compose form for admin-sent custom/bulk client emails (dashboard.EmailCampaign)."""

    subject  = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={"placeholder": "Email subject line"}),
    )
    heading  = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. Important account update (optional)"}),
        help_text="Large headline shown under the greeting. Leave blank to omit.",
    )
    message  = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10, "placeholder": "Write the email body here…"}),
        help_text="Plain text — blank lines start a new paragraph.",
    )
    cta_text = forms.CharField(
        max_length=100, required=False,
        widget=forms.TextInput(attrs={"placeholder": "e.g. View Dashboard (optional)"}),
        label="Button text",
    )
    cta_url  = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={"placeholder": "https://… (optional)"}),
        label="Button link",
    )

    # Social links — each optional. An icon only appears in the email footer
    # if its URL is filled in here.
    facebook_url  = forms.URLField(required=False, label="Facebook",
                                    widget=forms.URLInput(attrs={"placeholder": "https://facebook.com/…"}))
    twitter_url   = forms.URLField(required=False, label="Twitter / X",
                                    widget=forms.URLInput(attrs={"placeholder": "https://x.com/…"}))
    instagram_url = forms.URLField(required=False, label="Instagram",
                                    widget=forms.URLInput(attrs={"placeholder": "https://instagram.com/…"}))
    linkedin_url  = forms.URLField(required=False, label="LinkedIn",
                                    widget=forms.URLInput(attrs={"placeholder": "https://linkedin.com/…"}))
    telegram_url  = forms.URLField(required=False, label="Telegram",
                                    widget=forms.URLInput(attrs={"placeholder": "https://t.me/…"}))
    youtube_url   = forms.URLField(required=False, label="YouTube",
                                    widget=forms.URLInput(attrs={"placeholder": "https://youtube.com/…"}))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("cta_text") and not cleaned.get("cta_url"):
            self.add_error("cta_url", "Add a link, or clear the button text.")
        if cleaned.get("cta_url") and not cleaned.get("cta_text"):
            self.add_error("cta_text", "Add button text, or clear the link.")
        return cleaned

    def social_links(self) -> dict:
        """Non-empty {platform: url} pairs, ready for email_service.send_custom_email."""
        cd = self.cleaned_data
        links = {
            "facebook":  cd.get("facebook_url", ""),
            "twitter":   cd.get("twitter_url", ""),
            "instagram": cd.get("instagram_url", ""),
            "linkedin":  cd.get("linkedin_url", ""),
            "telegram":  cd.get("telegram_url", ""),
            "youtube":   cd.get("youtube_url", ""),
        }
        return {k: v for k, v in links.items() if v}


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

# CDN logo URLs for each asset — used in admin templates
ASSET_ICON_MAP: dict[str, str] = {
    # ── Stocks (Clearbit Logo API) ────────────────────────────────────────────
    "AAPL":  "https://logo.clearbit.com/apple.com",
    "MSFT":  "https://logo.clearbit.com/microsoft.com",
    "GOOGL": "https://logo.clearbit.com/google.com",
    "AMZN":  "https://logo.clearbit.com/amazon.com",
    "TSLA":  "https://logo.clearbit.com/tesla.com",
    "META":  "https://logo.clearbit.com/meta.com",
    "NVDA":  "https://logo.clearbit.com/nvidia.com",
    "JPM":   "https://logo.clearbit.com/jpmorganchase.com",
    "NFLX":  "https://logo.clearbit.com/netflix.com",
    "V":     "https://logo.clearbit.com/visa.com",
    "AMD":   "https://logo.clearbit.com/amd.com",
    "WMT":   "https://logo.clearbit.com/walmart.com",
    "DIS":   "https://logo.clearbit.com/disney.com",
    "PYPL":  "https://logo.clearbit.com/paypal.com",
    "COIN":  "https://logo.clearbit.com/coinbase.com",
    "BABA":  "https://logo.clearbit.com/alibaba.com",
    "INTC":  "https://logo.clearbit.com/intel.com",
    "GS":    "https://logo.clearbit.com/goldmansachs.com",
    "MS":    "https://logo.clearbit.com/morganstanley.com",
    "UBER":  "https://logo.clearbit.com/uber.com",
    "BAC":   "https://logo.clearbit.com/bankofamerica.com",
    # ── Crypto (cryptocurrency-icons via jsDelivr) ────────────────────────────
    "BTC":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/btc.svg",
    "ETH":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/eth.svg",
    "BNB":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/bnb.svg",
    "SOL":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/sol.svg",
    "XRP":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/xrp.svg",
    "ADA":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/ada.svg",
    "DOGE":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/doge.svg",
    "AVAX":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/avax.svg",
    "DOT":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/dot.svg",
    "MATIC": "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/matic.svg",
    "LTC":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/ltc.svg",
    "LINK":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/link.svg",
    "UNI":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/uni.svg",
    "ATOM":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/atom.svg",
    "SHIB":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/shib.svg",
    "TRX":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/trx.svg",
    "FIL":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/fil.svg",
    "NEAR":  "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/near.svg",
    "APT":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/apt.svg",
    "ARB":   "https://cdn.jsdelivr.net/npm/cryptocurrency-icons@0.18.1/svg/color/arb.svg",
}

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


# ─────────────────────────────────────────────────────────────────────────────
# FMP Asset Combobox Widget
# ─────────────────────────────────────────────────────────────────────────────

class FmpComboboxWidget(forms.Widget):
    """
    FMP-powered live asset search combobox for the admin panel.
    Uses VeltrixSync's dark green theme. Shows logo + symbol + name.
    """

    def render(self, name, value, attrs=None, renderer=None):
        attrs    = attrs or {}
        field_id = attrs.get("id", f"id_{name}")
        current  = str(value or "")

        # Build default list from ASSET_MAP so the dropdown isn't empty on open
        local = []
        for sym in ASSET_MAP["stock"]:
            local.append({"symbol": sym, "name": sym, "cat": "Stock"})
        for sym in ASSET_MAP["crypto"]:
            local.append({"symbol": sym, "name": sym, "cat": "Crypto"})
        for sym in ASSET_MAP["forex"]:
            local.append({"symbol": sym, "name": sym, "cat": "Forex"})

        local_json   = json.dumps(local)
        has_val      = "true" if current else "false"
        trigger_label = current or ""

        html = f"""
<style>
#fmp-trigger-{field_id}{{
  width:100%;display:flex;align-items:center;gap:10px;
  padding:0 12px;min-height:40px;box-sizing:border-box;
  background:#0e1a12;border:1px solid #1e3827;border-radius:6px;
  cursor:pointer;text-align:left;transition:border-color .15s;font-family:inherit;
}}
#fmp-trigger-{field_id}:hover{{border-color:#B0D45A;}}
#fmp-trigger-{field_id}.fmp-open-{field_id}{{border-color:#B0D45A;border-bottom-left-radius:0;border-bottom-right-radius:0;border-bottom-color:#1e3827;}}
#fmp-panel-{field_id}{{
  display:none;position:absolute;z-index:9999;left:0;right:0;
  background:#0e1a12;border:1px solid #B0D45A;border-top:none;
  border-bottom-left-radius:6px;border-bottom-right-radius:6px;
  box-shadow:0 12px 40px rgba(0,0,0,.7);
}}
#fmp-search-wrap-{field_id}{{
  display:flex;align-items:center;gap:8px;
  margin:10px 10px 6px;padding:0 10px;
  background:#0b1c11;border:1px solid #1e3827;border-radius:5px;
  min-height:34px;transition:border-color .15s;
}}
#fmp-search-wrap-{field_id}:focus-within{{border-color:#B0D45A;box-shadow:0 0 0 2px rgba(176,212,90,.15);}}
#fmp-search-{field_id}{{
  border:none!important;outline:none;flex:1;font-size:13px;
  background:transparent!important;color:#f0f0f0!important;
  padding:0;font-family:inherit;box-shadow:none!important;
}}
#fmp-search-{field_id}::placeholder{{color:#4a6655!important;}}
#fmp-list-{field_id}{{max-height:248px;overflow-y:auto;padding:4px 0;}}
#fmp-list-{field_id}::-webkit-scrollbar{{width:4px;}}
#fmp-list-{field_id}::-webkit-scrollbar-thumb{{background:#1e3827;border-radius:2px;}}
.fmp-opt-{field_id}{{display:flex;align-items:center;gap:10px;padding:8px 14px;cursor:pointer;transition:background .1s;}}
.fmp-opt-{field_id}:hover{{background:#132b1a;}}
.fmp-opt-{field_id}.fmp-sel-{field_id}{{background:rgba(176,212,90,.1);}}
@keyframes fmp-spin-{field_id}{{from{{transform:rotate(0deg);}}to{{transform:rotate(360deg);}}}}
</style>
<div style="position:relative;width:100%;">
  <button type="button" id="fmp-trigger-{field_id}">
    <div id="fmp-t-logo-wrap-{field_id}" style="display:{'flex' if current else 'none'};align-items:center;width:24px;height:24px;flex-shrink:0;">
      <img id="fmp-t-logo-{field_id}" src="https://images.financialmodelingprep.com/symbol/{current}.png"
           style="width:24px;height:24px;object-fit:contain;border-radius:3px;"
           onerror="this.style.display='none';document.getElementById('fmp-t-av-{field_id}').style.display='flex'">
      <div id="fmp-t-av-{field_id}" style="display:none;width:24px;height:24px;background:#1e3827;border-radius:4px;
           color:#B0D45A;font-size:8px;font-weight:800;align-items:center;justify-content:center;">
        {current[:3] if current else ''}
      </div>
    </div>
    <span id="fmp-t-label-{field_id}" style="flex:1;font-size:13.5px;color:{'#f0f0f0' if current else '#4a6655'};white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">
      {trigger_label if trigger_label else 'Search market / asset…'}
    </span>
    <svg id="fmp-chevron-{field_id}" style="width:16px;height:16px;flex-shrink:0;color:#4a6655;transition:transform .2s;"
         viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M6 9l6 6 6-6"/></svg>
  </button>
  <input type="hidden" name="{name}" id="{field_id}" value="{current}">
  <div id="fmp-panel-{field_id}">
    <div id="fmp-search-wrap-{field_id}">
      <svg style="width:14px;height:14px;color:#4a6655;flex-shrink:0;" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="11" cy="11" r="8"/><path d="M21 21l-4.35-4.35"/>
      </svg>
      <input type="text" id="fmp-search-{field_id}" placeholder="Search any asset, stock, crypto, forex…" autocomplete="off">
      <svg id="fmp-spin-{field_id}" style="display:none;width:14px;height:14px;flex-shrink:0;color:#B0D45A;animation:fmp-spin-{field_id} .7s linear infinite;"
           viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/>
      </svg>
    </div>
    <div id="fmp-list-{field_id}"></div>
  </div>
</div>
<script>
(function(){{
  var LOCAL   = {local_json};
  var trigger = document.getElementById('fmp-trigger-{field_id}');
  var panel   = document.getElementById('fmp-panel-{field_id}');
  var search  = document.getElementById('fmp-search-{field_id}');
  var list    = document.getElementById('fmp-list-{field_id}');
  var spin    = document.getElementById('fmp-spin-{field_id}');
  var hidden  = document.getElementById('{field_id}');
  var chevron = document.getElementById('fmp-chevron-{field_id}');
  var tLogoWrap = document.getElementById('fmp-t-logo-wrap-{field_id}');
  var tLogo   = document.getElementById('fmp-t-logo-{field_id}');
  var tAv     = document.getElementById('fmp-t-av-{field_id}');
  var tLabel  = document.getElementById('fmp-t-label-{field_id}');
  if (!trigger) return;

  var open = false, fmpTm, currentSym = {json.dumps(current)};

  function openPanel() {{
    open = true; panel.style.display = 'block';
    trigger.classList.add('fmp-open-{field_id}');
    chevron.style.transform = 'rotate(180deg)';
    search.value = '';
    renderList(LOCAL.slice(0, 50));
    setTimeout(function() {{ search.focus(); }}, 40);
  }}

  function closePanel() {{
    open = false; panel.style.display = 'none';
    trigger.classList.remove('fmp-open-{field_id}');
    chevron.style.transform = '';
    spin.style.display = 'none';
    clearTimeout(fmpTm);
  }}

  trigger.addEventListener('click', function(e) {{ e.stopPropagation(); open ? closePanel() : openPanel(); }});
  document.addEventListener('click', function(e) {{ if (open && !panel.contains(e.target) && e.target !== trigger) closePanel(); }});

  search.addEventListener('input', function() {{
    var q = search.value.trim();
    if (!q) {{ renderList(LOCAL.slice(0, 50)); spin.style.display = 'none'; return; }}
    renderList(filterLocal(q));
    clearTimeout(fmpTm);
    spin.style.display = 'block';
    fmpTm = setTimeout(function() {{ fetchFmp(q); }}, 380);
  }});
  search.addEventListener('keydown', function(e) {{ if (e.key === 'Escape') closePanel(); }});

  function filterLocal(q) {{
    var ql = q.toLowerCase();
    return LOCAL.filter(function(it) {{ return (it.symbol + ' ' + it.name).toLowerCase().indexOf(ql) !== -1; }}).slice(0, 30);
  }}

  function fetchFmp(q) {{
    fetch('/panel/api/fmp-search/?q=' + encodeURIComponent(q))
      .then(function(r) {{ return r.ok ? r.json() : []; }})
      .then(function(items) {{
        spin.style.display = 'none';
        if (!Array.isArray(items)) return;
        var localSyms = new Set(filterLocal(q).map(function(x) {{ return x.symbol; }}));
        var extra = items.filter(function(it) {{ return it.symbol && !localSyms.has(it.symbol); }})
                        .map(function(it) {{ return {{symbol: it.symbol, name: it.name || '', cat: '', fmp: true}}; }});
        renderList(filterLocal(q).concat(extra));
      }})
      .catch(function() {{ spin.style.display = 'none'; }});
  }}

  function selectItem(sym, name) {{
    currentSym = sym; hidden.value = sym;
    tLabel.textContent = name ? sym + '  —  ' + name : sym;
    tLabel.style.color = '#f0f0f0';
    tLogoWrap.style.display = 'flex';
    tLogo.style.display = 'block';
    tLogo.src = 'https://images.financialmodelingprep.com/symbol/' + sym + '.png';
    tAv.textContent = sym.slice(0, 3); tAv.style.display = 'none';
    closePanel();
  }}

  function renderList(items) {{
    list.innerHTML = '';
    if (!items.length) {{
      var em = document.createElement('div');
      em.style.cssText = 'padding:14px 16px;color:#4a6655;font-size:13px;text-align:center;';
      em.textContent = 'No matching assets found';
      list.appendChild(em); return;
    }}
    items.forEach(function(it) {{
      if (!it.symbol) return;
      var row = document.createElement('div');
      row.className = 'fmp-opt-{field_id}' + (it.symbol === currentSym ? ' fmp-sel-{field_id}' : '');
      var img = document.createElement('img');
      img.src = 'https://images.financialmodelingprep.com/symbol/' + it.symbol + '.png';
      img.style.cssText = 'width:28px;height:28px;object-fit:contain;flex-shrink:0;border-radius:4px;';
      var av = document.createElement('div');
      av.style.cssText = 'display:none;width:28px;height:28px;background:#1e3827;border-radius:4px;' +
                         'color:#B0D45A;font-size:8px;font-weight:800;align-items:center;justify-content:center;flex-shrink:0;';
      av.textContent = it.symbol.slice(0, 3);
      img.onerror = function() {{ img.style.display = 'none'; av.style.display = 'flex'; }};
      var info = document.createElement('div'); info.style.cssText = 'flex:1;min-width:0;';
      var symEl = document.createElement('span');
      symEl.style.cssText = 'font-weight:700;font-size:13px;color:#f0f0f0;'; symEl.textContent = it.symbol;
      info.appendChild(symEl);
      if (it.name && it.name !== it.symbol) {{
        var nm = document.createElement('span');
        nm.style.cssText = 'color:#8fa896;font-size:12px;margin-left:6px;'; nm.textContent = '— ' + it.name;
        info.appendChild(nm);
      }}
      var right = document.createElement('div'); right.style.cssText = 'display:flex;align-items:center;gap:5px;flex-shrink:0;';
      if (it.cat) {{
        var catB = document.createElement('span');
        var catColor = it.cat==='Crypto'?'rgba(34,197,94,.2)':it.cat==='Forex'?'rgba(251,191,36,.2)':'rgba(176,212,90,.15)';
        var catText  = it.cat==='Crypto'?'#22c55e':it.cat==='Forex'?'#fbbf24':'#B0D45A';
        catB.style.cssText = 'font-size:10px;padding:1px 5px;border-radius:3px;font-weight:600;background:'+catColor+';color:'+catText+';text-transform:uppercase;';
        catB.textContent = it.cat; right.appendChild(catB);
      }}
      if (it.fmp) {{
        var fmpB = document.createElement('span');
        fmpB.style.cssText = 'font-size:10px;padding:1px 5px;border-radius:3px;font-weight:600;background:rgba(176,212,90,.15);color:#B0D45A;';
        fmpB.textContent = 'FMP'; right.appendChild(fmpB);
      }}
      if (it.symbol === currentSym) {{
        var chk = document.createElement('span');
        chk.style.cssText = 'color:#B0D45A;font-size:15px;font-weight:700;margin-left:2px;'; chk.textContent = '✓';
        right.appendChild(chk);
      }}
      row.appendChild(img); row.appendChild(av); row.appendChild(info); row.appendChild(right);
      row.addEventListener('mousedown', function(e) {{ e.preventDefault(); selectItem(it.symbol, it.name || ''); }});
      list.appendChild(row);
    }});
  }}
}})();
</script>"""
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        return data.get(name, "")


class AddTradeForm(forms.Form):
    """Used for both single-investor and bulk trade injection."""
    DIRECTION_CHOICES = [("Buy", "Buy"), ("Sell", "Sell")]
    STATUS_CHOICES = [("open", "Open"), ("closed", "Closed"), ("pending", "Pending")]
    DURATION_CHOICES = [
        ("2m", "2 Minutes"), ("5m", "5 Minutes"), ("10m", "10 Minutes"),
        ("15m", "15 Minutes"), ("30m", "30 Minutes"), ("1h", "1 Hour"),
        ("2h", "2 Hours"), ("4h", "4 Hours"), ("6h", "6 Hours"),
        ("12h", "12 Hours"), ("1d", "1 Day"), ("3d", "3 Days"), ("1w", "1 Week"),
    ]

    asset        = forms.CharField(max_length=100, label="Market / Asset",
                                   widget=FmpComboboxWidget())
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
        if not asset:
            raise forms.ValidationError("Please select an asset.")
        return asset


class TraderPositionForm(forms.ModelForm):
    class Meta:
        model  = TraderPosition
        fields = ["market", "direction", "invested", "pl", "value", "sell_price", "buy_price"]
        widgets = {
            "market": forms.TextInput(attrs={"placeholder": "e.g. BTC/USD"}),
        }


_EDIT_TRADE_TYPE_CHOICES      = [("stock", "Stock"), ("crypto", "Crypto"), ("forex", "Forex")]
_EDIT_TRADE_DIRECTION_CHOICES = [("Buy", "Buy"), ("Sell", "Sell")]
_EDIT_TRADE_STATUS_CHOICES    = [("open", "Open"), ("closed", "Closed"), ("pending", "Pending")]
_EDIT_TRADE_DURATION_CHOICES  = [
    ("2m", "2 Minutes"), ("5m", "5 Minutes"), ("10m", "10 Minutes"),
    ("15m", "15 Minutes"), ("30m", "30 Minutes"), ("1h", "1 Hour"),
    ("2h", "2 Hours"), ("4h", "4 Hours"), ("6h", "6 Hours"),
    ("12h", "12 Hours"), ("1d", "1 Day"), ("3d", "3 Days"), ("1w", "1 Week"),
]


class EditCopyTradeForm(forms.ModelForm):
    """Edit an existing CopyTrade record (does NOT recalculate PNL)."""

    class Meta:
        model  = CopyTrade
        fields = ["asset_type", "asset", "direction", "entry", "earning_pct", "pnl", "duration", "status"]
        widgets = {
            "asset_type":  forms.Select(choices=_EDIT_TRADE_TYPE_CHOICES,      attrs={"class": _FC}),
            "asset":       forms.TextInput(attrs={"class": _FC}),
            "direction":   forms.Select(choices=_EDIT_TRADE_DIRECTION_CHOICES, attrs={"class": _FC}),
            "entry":       forms.NumberInput(attrs={"step": "0.01", "class": _FC}),
            "earning_pct": forms.NumberInput(attrs={"step": "0.01", "class": _FC}),
            "pnl":         forms.NumberInput(attrs={"step": "0.01", "class": _FC}),
            "duration":    forms.Select(choices=_EDIT_TRADE_DURATION_CHOICES,  attrs={"class": _FC}),
            "status":      forms.Select(choices=_EDIT_TRADE_STATUS_CHOICES,    attrs={"class": _FC}),
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


