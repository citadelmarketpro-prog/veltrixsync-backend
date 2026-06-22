from django.contrib import admin
from .models import (
    AdminWallet, CopyRelationship, DummyCopier, Notification, PortfolioAllocation,
    TradeHistory, Trader, TraderAsset, TraderPosition, TraderSection,
    TraderTag, Transaction, User, CopyTrade,
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display   = ("email", "username", "first_name", "last_name", "balance", "roi", "kyc_status", "allow_transfer", "date_joined")
    list_filter    = ("kyc_status", "allow_transfer", "is_active", "is_staff")
    search_fields  = ("email", "username", "first_name", "last_name")
    ordering       = ("-date_joined",)
    list_editable  = ("allow_transfer",)
    readonly_fields = ("date_joined", "last_login", "password")
    fieldsets = (
        ("Account", {
            "fields": ("email", "username", "password", "is_active", "is_staff", "is_superuser"),
        }),
        ("Profile", {
            "fields": ("first_name", "last_name", "bio", "avatar", "phone"),
        }),
        ("Financials", {
            "fields": ("balance", "roi", "percentage_roi"),
        }),
        ("Permissions", {
            "fields": ("allow_transfer",),
            "description": "Control which features this user is allowed to access.",
        }),
        ("KYC", {
            "fields": (
                "kyc_status", "kyc_submitted_at", "kyc_reviewed_at", "kyc_reject_reason",
                "title", "date_of_birth", "street_address", "city", "province", "zipcode",
                "id_type", "id_front", "id_back",
            ),
            "classes": ("collapse",),
        }),
        ("Timestamps", {
            "fields": ("date_joined", "last_login"),
        }),
    )


@admin.register(CopyTrade)
class CopyTradeAdmin(admin.ModelAdmin):
    list_display  = ("user", "asset", "asset_type", "direction", "earning_pct", "pnl", "status", "created_at")
    list_filter   = ("status", "asset_type", "direction")
    search_fields = ("user__email", "asset")
    ordering      = ("-created_at",)


# ── Trader inline helpers ──────────────────────────────────────────────────────

class DummyCopierInline(admin.TabularInline):
    model  = DummyCopier
    extra  = 1
    fields = ("name", "started_at", "allocated_amount", "pl")


class TraderSectionInline(admin.TabularInline):
    model  = TraderSection
    extra  = 1
    fields = ("section", "rank")


class TraderAssetInline(admin.TabularInline):
    model  = TraderAsset
    extra  = 1
    fields = ("order", "icon", "name", "ticker", "avg_return", "avg_risk", "risk_label", "success_rate")


class PortfolioAllocationInline(admin.TabularInline):
    model  = PortfolioAllocation
    extra  = 1
    fields = ("order", "label", "pct", "color")


@admin.register(Trader)
class TraderAdmin(admin.ModelAdmin):
    list_display   = ("name", "specialty", "risk_level", "market_category", "roi", "copiers_count", "win_rate")
    list_filter    = ("risk_level", "market_category")
    search_fields  = ("name", "specialty", "bio")
    ordering       = ("name",)
    filter_horizontal = ("trader_tags",)
    inlines        = [TraderSectionInline, TraderAssetInline, PortfolioAllocationInline, DummyCopierInline]
    fieldsets      = (
        ("Identity", {
            "fields": ("name", "specialty", "bio", "avatar", "avatar_color", "trader_tags"),
        }),
        ("List stats", {
            "fields": (
                "roi", "copiers_count", "followers_count",
                "min_capital", "trading_days", "win_rate",
                "risk_level", "market_category",
            ),
        }),
        ("Detail stats", {
            "fields": (
                "master_pnl", "account_assets", "max_drawdown",
                "cum_earnings", "cum_copiers", "profit_share",
            ),
        }),
    )


@admin.register(TraderTag)
class TraderTagAdmin(admin.ModelAdmin):
    list_display  = ("name",)
    search_fields = ("name",)
    ordering      = ("name",)


@admin.register(TraderSection)
class TraderSectionAdmin(admin.ModelAdmin):
    list_display  = ("trader", "section", "rank")
    list_filter   = ("section",)
    search_fields = ("trader__name",)
    ordering      = ("section", "rank")
    list_editable = ("rank",)


@admin.register(TraderAsset)
class TraderAssetAdmin(admin.ModelAdmin):
    list_display  = ("trader", "name", "ticker", "avg_return", "success_rate", "order")
    list_filter   = ("trader",)
    search_fields = ("trader__name", "name", "ticker")
    ordering      = ("trader", "order")
    list_editable = ("order",)


@admin.register(PortfolioAllocation)
class PortfolioAllocationAdmin(admin.ModelAdmin):
    list_display  = ("trader", "label", "pct", "color", "order")
    list_filter   = ("trader",)
    search_fields = ("trader__name", "label")
    ordering      = ("trader", "order")
    list_editable = ("order",)


@admin.register(TraderPosition)
class TraderPositionAdmin(admin.ModelAdmin):
    list_display  = ("trader", "market", "direction", "invested", "pl", "value", "opened_at")
    list_filter   = ("direction", "trader")
    search_fields = ("trader__name", "market")
    ordering      = ("-opened_at",)
    readonly_fields = ("opened_at",)


@admin.register(TradeHistory)
class TradeHistoryAdmin(admin.ModelAdmin):
    list_display  = ("trader", "name", "order_type", "position", "pl", "open_date", "close_date")
    list_filter   = ("order_type", "position", "trader")
    search_fields = ("trader__name", "name")
    ordering      = ("-close_date",)


@admin.register(CopyRelationship)
class CopyRelationshipAdmin(admin.ModelAdmin):
    list_display  = ("copier", "trader", "allocated_amount", "pl", "started_at")
    list_filter   = ("trader",)
    search_fields = ("copier__email", "copier__username", "trader__name")
    ordering      = ("-started_at",)
    readonly_fields = ("started_at",)


@admin.register(DummyCopier)
class DummyCopierAdmin(admin.ModelAdmin):
    list_display   = ("trader", "name", "allocated_amount", "pl", "started_at")
    list_filter    = ("trader",)
    search_fields  = ("trader__name", "name")
    ordering       = ("trader", "-started_at")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display  = ("user", "notif_type", "title", "is_read", "created_at")
    list_filter   = ("notif_type", "is_read")
    search_fields = ("user__email", "title", "body")
    ordering      = ("-created_at",)
    actions       = ["mark_read", "mark_unread"]

    @admin.action(description="Mark selected as read")
    def mark_read(self, _request, queryset):
        queryset.update(is_read=True)

    @admin.action(description="Mark selected as unread")
    def mark_unread(self, _request, queryset):
        queryset.update(is_read=False)


@admin.register(AdminWallet)
class AdminWalletAdmin(admin.ModelAdmin):
    list_display  = ("name", "symbol", "network", "address", "is_active", "order")
    list_filter   = ("is_active", "symbol")
    search_fields = ("name", "symbol", "address")
    ordering      = ("order", "name")
    list_editable = ("is_active", "order")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display  = ("user", "tx_type", "asset", "amount_usd", "status", "tx_id", "created_at")
    list_filter   = ("tx_type", "status", "asset")
    search_fields = ("user__email", "tx_id", "asset")
    ordering      = ("-created_at",)
    readonly_fields = ("tx_id", "created_at")
    actions       = ["approve_transactions", "reject_transactions"]

    @admin.action(description="Approve selected transactions")
    def approve_transactions(self, request, queryset):
        from decimal import Decimal
        for tx in queryset.filter(status="pending"):
            tx.status = "completed"
            tx.save(update_fields=["status"])
            user = tx.user
            if tx.tx_type == "deposit":
                user.balance = (user.balance or Decimal("0")) + tx.amount_usd
                user.save(update_fields=["balance"])
            elif tx.tx_type == "withdrawal":
                field = tx.withdraw_from or "balance"
                current = (user.balance if field == "balance" else user.roi) or Decimal("0")
                if field == "balance":
                    user.balance = max(current - tx.amount_usd, Decimal("0"))
                    user.save(update_fields=["balance"])
                else:
                    user.roi = max(current - tx.amount_usd, Decimal("0"))
                    user.save(update_fields=["roi"])
        self.message_user(request, "Selected transactions approved and balances updated.")

    @admin.action(description="Reject selected transactions")
    def reject_transactions(self, request, queryset):
        for tx in queryset.filter(status="pending"):
            tx.status = "rejected"
            tx.save(update_fields=["status"])
        self.message_user(request, "Selected transactions rejected.")
