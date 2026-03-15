from django.contrib import admin
from .models import (
    AdminWallet, CopyRelationship, Notification, PortfolioAllocation,
    TradeHistory, Trader, TraderAsset, TraderPosition, TraderSection,
    TraderTag, Transaction, User,
)

admin.site.register(User)


# ── Trader inline helpers ──────────────────────────────────────────────────────

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
    inlines        = [TraderSectionInline, TraderAssetInline, PortfolioAllocationInline]
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
        for tx in queryset.filter(status="pending"):
            tx.status = "completed"
            tx.save(update_fields=["status"])
            if tx.tx_type == "deposit":
                user = tx.user
                user.balance = (user.balance or 0) + tx.amount_usd
                user.save(update_fields=["balance"])
        self.message_user(request, "Selected transactions approved and balances updated.")

    @admin.action(description="Reject selected transactions")
    def reject_transactions(self, request, queryset):
        for tx in queryset.filter(status="pending"):
            tx.status = "rejected"
            tx.save(update_fields=["status"])
        self.message_user(request, "Selected transactions rejected.")
