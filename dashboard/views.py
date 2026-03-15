from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from core.models import (
    AdminWallet, CopyRelationship, CopyTrade, Notification, PortfolioAllocation,
    Trader, TraderAsset, TraderPosition, TradeHistory, TraderSection, TraderTag, Transaction,
)
from .decorators import superuser_required
from .forms import (
    AdminWalletForm, AdjustFundsForm, BulkCopyTradeForm, CopyTradeForm, PortfolioAllocationForm,
    RejectKycForm, TraderAssetForm, TradeHistoryForm, TraderForm, TraderPositionForm,
    TraderSectionForm, TraderTagForm, UserCreateForm, UserEditForm,
)

User = get_user_model()

# ── Auth ──────────────────────────────────────────────────────────────────────

def panel_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect("panel:dashboard")
    error = None
    if request.method == "POST":
        user = authenticate(request, username=request.POST.get("email","").strip(), password=request.POST.get("password",""))
        if user and user.is_superuser:
            login(request, user)
            return redirect(request.GET.get("next", "panel:dashboard"))
        error = "Invalid credentials or insufficient privileges."
    return render(request, "panel/auth/login.html", {"error": error})


def panel_logout(request):
    logout(request)
    return redirect("panel:login")

# ── Dashboard ─────────────────────────────────────────────────────────────────

@superuser_required
def dashboard_home(request):
    return render(request, "panel/dashboard.html", {
        "total_users":           User.objects.count(),
        "kyc_pending":           User.objects.filter(kyc_status__in=["submitted","under_review"]).count(),
        "kyc_approved":          User.objects.filter(kyc_status="approved").count(),
        "total_traders":         Trader.objects.count(),
        "total_copies":          CopyRelationship.objects.count(),
        "pending_tx":            Transaction.objects.filter(status="pending").count(),
        "completed_deposits":    Transaction.objects.filter(tx_type="deposit",    status="completed").aggregate(s=Sum("amount_usd"))["s"] or 0,
        "completed_withdrawals": Transaction.objects.filter(tx_type="withdrawal", status="completed").aggregate(s=Sum("amount_usd"))["s"] or 0,
        "total_balance":         User.objects.aggregate(s=Sum("balance"))["s"] or 0,
        "total_profit":          User.objects.aggregate(s=Sum("profit"))["s"] or 0,
        "recent_tx":             Transaction.objects.select_related("user").order_by("-created_at")[:8],
        "recent_users":          User.objects.order_by("-date_joined")[:8],
    })

# ── Users ─────────────────────────────────────────────────────────────────────

@superuser_required
def user_list(request):
    qs = User.objects.order_by("-date_joined")
    q  = request.GET.get("q","").strip()
    kf = request.GET.get("kyc","")
    if q:  qs = qs.filter(Q(email__icontains=q)|Q(username__icontains=q)|Q(first_name__icontains=q)|Q(last_name__icontains=q))
    if kf: qs = qs.filter(kyc_status=kf)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "panel/users/list.html", {"page_obj": page, "q": q, "kyc_filter": kf, "kyc_choices": User.KYC_STATUS_CHOICES})


@superuser_required
def user_create(request):
    form = UserCreateForm(request.POST or None)
    if form.is_valid():
        user = form.save()
        messages.success(request, f"User {user.email} created.")
        return redirect("panel:user_detail", pk=user.pk)
    return render(request, "panel/users/create.html", {"form": form})


@superuser_required
def user_detail(request, pk):
    obj = get_object_or_404(User, pk=pk)
    return render(request, "panel/users/detail.html", {
        "obj": obj,
        "transactions": Transaction.objects.filter(user=obj).order_by("-created_at")[:10],
        "copies": CopyRelationship.objects.filter(copier=obj).select_related("trader"),
    })


@superuser_required
def user_edit(request, pk):
    obj  = get_object_or_404(User, pk=pk)
    form = UserEditForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        messages.success(request, f"User {obj.email} updated.")
        return redirect("panel:user_detail", pk=pk)
    return render(request, "panel/users/edit.html", {"form": form, "obj": obj})


@superuser_required
def user_delete(request, pk):
    obj = get_object_or_404(User, pk=pk)
    if request.method == "POST":
        email = obj.email
        obj.delete()
        messages.success(request, f"User {email} deleted.")
        return redirect("panel:user_list")
    return render(request, "panel/confirm_delete.html", {
        "title": "Delete user?",
        "subtitle": obj.email,
        "warning": "This will permanently delete the user and all their data.",
        "cancel_url": f"/panel/users/{pk}/",
    })


@superuser_required
@require_POST
def user_approve_kyc(request, pk):
    obj = get_object_or_404(User, pk=pk)
    obj.kyc_status = "approved"
    obj.kyc_reviewed_at = timezone.now()
    obj.kyc_reject_reason = ""
    obj.save(update_fields=["kyc_status","kyc_reviewed_at","kyc_reject_reason"])
    Notification.objects.create(user=obj, notif_type="kyc", title="KYC Approved",
        body="Your identity verification has been approved. You now have full access.")
    messages.success(request, f"KYC approved for {obj.email}.")
    return redirect("panel:user_detail", pk=pk)


@superuser_required
def user_reject_kyc(request, pk):
    obj  = get_object_or_404(User, pk=pk)
    form = RejectKycForm(request.POST or None)
    if form.is_valid():
        obj.kyc_status = "rejected"
        obj.kyc_reviewed_at = timezone.now()
        obj.kyc_reject_reason = form.cleaned_data["reason"]
        obj.save(update_fields=["kyc_status","kyc_reviewed_at","kyc_reject_reason"])
        Notification.objects.create(user=obj, notif_type="kyc", title="KYC Rejected",
            body="Your KYC was rejected. Reason: " + form.cleaned_data["reason"])
        messages.success(request, f"KYC rejected for {obj.email}.")
        return redirect("panel:user_detail", pk=pk)
    return render(request, "panel/users/reject_kyc.html", {"form": form, "obj": obj})


@superuser_required
def user_adjust_funds(request, pk):
    obj  = get_object_or_404(User, pk=pk)
    form = AdjustFundsForm(request.POST or None)
    if form.is_valid():
        field   = form.cleaned_data["field"]
        mode    = form.cleaned_data["mode"]
        amount  = form.cleaned_data["amount"]
        current = getattr(obj, field)
        if   mode == "add":      setattr(obj, field, current + amount)
        elif mode == "subtract": setattr(obj, field, max(Decimal("0"), current - amount))
        else:                    setattr(obj, field, amount)
        obj.save(update_fields=[field])
        messages.success(request, f"{field.capitalize()} updated for {obj.email}.")
        return redirect("panel:user_detail", pk=pk)
    return render(request, "panel/users/adjust_funds.html", {"form": form, "obj": obj})

# ── Traders ───────────────────────────────────────────────────────────────────

@superuser_required
def trader_list(request):
    qs = Trader.objects.prefetch_related("section_memberships").order_by("name")
    q  = request.GET.get("q","").strip()
    if q: qs = qs.filter(Q(name__icontains=q)|Q(specialty__icontains=q))
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "panel/traders/list.html", {"page_obj": page, "q": q})


@superuser_required
def trader_create(request):
    form = TraderForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        trader = form.save()
        messages.success(request, f"Trader '{trader.name}' created.")
        return redirect("panel:trader_detail", pk=trader.pk)
    return render(request, "panel/traders/form.html", {"form": form, "action": "Create"})


@superuser_required
def trader_detail(request, pk):
    t = get_object_or_404(Trader, pk=pk)
    all_rels = CopyRelationship.objects.filter(trader=t).select_related("copier")
    return render(request, "panel/traders/detail.html", {
        "obj":             t,
        "sections":        t.section_memberships.all(),
        "assets":          t.trader_assets.all(),
        "allocs":          t.portfolio_allocations.all(),
        "copiers":         all_rels.filter(status="active"),
        "cancel_requests": all_rels.filter(status="cancel_requested"),
        "tags":            t.trader_tags.all(),
        "positions":       t.positions.all(),
        "history":         t.trade_history.all(),
    })


@superuser_required
def trader_edit(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = TraderForm(request.POST or None, request.FILES or None, instance=trader)
    if form.is_valid():
        form.save()
        messages.success(request, "Trader updated.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/form.html", {"form": form, "obj": trader, "action": "Edit"})


@superuser_required
def trader_delete(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    if request.method == "POST":
        name = trader.name
        trader.delete()
        messages.success(request, f"Trader '{name}' deleted.")
        return redirect("panel:trader_list")
    return render(request, "panel/confirm_delete.html", {
        "title": "Delete trader?",
        "subtitle": trader.name,
        "warning": "All related data (positions, history, copiers) will be permanently removed.",
        "cancel_url": f"/panel/traders/{pk}/",
    })


@superuser_required
@require_POST
def trader_disconnect_copier(request, pk, copier_pk):
    rel = get_object_or_404(CopyRelationship, trader_id=pk, copier_id=copier_pk)
    email = rel.copier.email
    rel.delete()
    messages.success(request, f"Disconnected {email} from trader.")
    return redirect("panel:trader_detail", pk=pk)


@superuser_required
def trader_add_section(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = TraderSectionForm(request.POST or None)
    if form.is_valid():
        sec = form.save(commit=False)
        sec.trader = trader
        sec.save()
        messages.success(request, "Section added.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/section_form.html", {"form": form, "obj": trader})


@superuser_required
@require_POST
def trader_remove_section(request, pk, section_pk):
    get_object_or_404(TraderSection, pk=section_pk, trader_id=pk).delete()
    messages.success(request, "Section removed.")
    return redirect("panel:trader_detail", pk=pk)


@superuser_required
def trader_add_asset(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = TraderAssetForm(request.POST or None)
    if form.is_valid():
        a = form.save(commit=False)
        a.trader = trader
        a.save()
        messages.success(request, "Asset added.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/asset_form.html", {"form": form, "obj": trader})


@superuser_required
def trader_add_allocation(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = PortfolioAllocationForm(request.POST or None)
    if form.is_valid():
        a = form.save(commit=False)
        a.trader = trader
        a.save()
        messages.success(request, "Allocation added.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/allocation_form.html", {"form": form, "obj": trader})


@superuser_required
def trader_edit_asset(request, pk, asset_pk):
    trader = get_object_or_404(Trader, pk=pk)
    asset  = get_object_or_404(TraderAsset, pk=asset_pk, trader=trader)
    form   = TraderAssetForm(request.POST or None, request.FILES or None, instance=asset)
    if form.is_valid():
        form.save()
        messages.success(request, "Asset updated.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/asset_form.html", {"form": form, "obj": trader, "editing": True})


@superuser_required
@require_POST
def trader_delete_asset(request, pk, asset_pk):
    asset = get_object_or_404(TraderAsset, pk=asset_pk, trader_id=pk)
    asset.delete()
    messages.success(request, "Asset deleted.")
    return redirect("panel:trader_detail", pk=pk)


@superuser_required
def trader_edit_allocation(request, pk, alloc_pk):
    trader = get_object_or_404(Trader, pk=pk)
    alloc  = get_object_or_404(PortfolioAllocation, pk=alloc_pk, trader=trader)
    form   = PortfolioAllocationForm(request.POST or None, instance=alloc)
    if form.is_valid():
        form.save()
        messages.success(request, "Allocation updated.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/allocation_form.html", {"form": form, "obj": trader, "editing": True})


@superuser_required
@require_POST
def trader_delete_allocation(request, pk, alloc_pk):
    alloc = get_object_or_404(PortfolioAllocation, pk=alloc_pk, trader_id=pk)
    alloc.delete()
    messages.success(request, "Allocation deleted.")
    return redirect("panel:trader_detail", pk=pk)


@superuser_required
def trader_add_position(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = TraderPositionForm(request.POST or None)
    if form.is_valid():
        pos = form.save(commit=False)
        pos.trader = trader
        pos.save()
        messages.success(request, "Position added.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/position_form.html", {"form": form, "obj": trader, "action": "Add"})


@superuser_required
def trader_edit_position(request, pk, pos_pk):
    trader = get_object_or_404(Trader, pk=pk)
    pos    = get_object_or_404(TraderPosition, pk=pos_pk, trader=trader)
    form   = TraderPositionForm(request.POST or None, instance=pos)
    if form.is_valid():
        form.save()
        messages.success(request, "Position updated.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/position_form.html", {"form": form, "obj": trader, "action": "Edit"})


@superuser_required
@require_POST
def trader_delete_position(request, pk, pos_pk):
    get_object_or_404(TraderPosition, pk=pos_pk, trader_id=pk).delete()
    messages.success(request, "Position deleted.")
    return redirect("panel:trader_detail", pk=pk)


@superuser_required
def trader_add_history(request, pk):
    trader = get_object_or_404(Trader, pk=pk)
    form   = TradeHistoryForm(request.POST or None)
    if form.is_valid():
        h = form.save(commit=False)
        h.trader = trader
        h.save()
        messages.success(request, "Trade history entry added.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/history_form.html", {"form": form, "obj": trader, "action": "Add"})


@superuser_required
def trader_edit_history(request, pk, hist_pk):
    trader = get_object_or_404(Trader, pk=pk)
    hist   = get_object_or_404(TradeHistory, pk=hist_pk, trader=trader)
    form   = TradeHistoryForm(request.POST or None, instance=hist)
    if form.is_valid():
        form.save()
        messages.success(request, "Trade history updated.")
        return redirect("panel:trader_detail", pk=pk)
    return render(request, "panel/traders/history_form.html", {"form": form, "obj": trader, "action": "Edit"})


@superuser_required
@require_POST
def trader_delete_history(request, pk, hist_pk):
    get_object_or_404(TradeHistory, pk=hist_pk, trader_id=pk).delete()
    messages.success(request, "Trade history deleted.")
    return redirect("panel:trader_detail", pk=pk)


# ── Transactions ──────────────────────────────────────────────────────────────

@superuser_required
def transaction_list(request):
    qs = Transaction.objects.select_related("user").order_by("-created_at")
    q  = request.GET.get("q","").strip()
    sf = request.GET.get("status","")
    tf = request.GET.get("type","")
    if q:  qs = qs.filter(Q(user__email__icontains=q)|Q(asset__icontains=q))
    if sf: qs = qs.filter(status=sf)
    if tf: qs = qs.filter(tx_type=tf)
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "panel/transactions/list.html", {
        "page_obj": page, "q": q, "status_f": sf, "type_f": tf,
        "status_choices": Transaction.STATUS_CHOICES, "type_choices": Transaction.TX_TYPE_CHOICES,
    })


@superuser_required
def transaction_detail(request, pk):
    return render(request, "panel/transactions/detail.html", {"obj": get_object_or_404(Transaction, pk=pk)})


@superuser_required
@require_POST
def transaction_approve(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    if tx.status != "pending":
        messages.error(request, "Only pending transactions can be approved.")
        return redirect("panel:transaction_detail", pk=pk)
    tx.status = "completed"
    tx.save(update_fields=["status"])
    user = tx.user
    if tx.tx_type == "deposit":
        user.balance += tx.amount_usd
        user.save(update_fields=["balance"])
        Notification.objects.create(user=user, notif_type="wallet", title="Deposit Confirmed",
            body=f"Your deposit of ${tx.amount_usd:,.2f} ({tx.asset}) has been confirmed and added to your balance.")
        messages.success(request, f"Deposit approved — ${tx.amount_usd:,.2f} added to {user.email}.")
    else:
        user.balance = max(Decimal("0"), user.balance - tx.amount_usd)
        user.save(update_fields=["balance"])
        Notification.objects.create(user=user, notif_type="wallet", title="Withdrawal Approved",
            body=f"Your withdrawal of ${tx.amount_usd:,.2f} ({tx.asset}) has been approved and processed.")
        messages.success(request, f"Withdrawal approved — ${tx.amount_usd:,.2f} deducted from {user.email}.")
    return redirect("panel:transaction_detail", pk=pk)


@superuser_required
@require_POST
def transaction_reject(request, pk):
    tx = get_object_or_404(Transaction, pk=pk)
    if tx.status != "pending":
        messages.error(request, "Only pending transactions can be rejected.")
        return redirect("panel:transaction_detail", pk=pk)
    tx.status = "rejected"
    tx.save(update_fields=["status"])
    Notification.objects.create(user=tx.user, notif_type="wallet", title="Transaction Rejected",
        body=f"Your {tx.tx_type} of ${tx.amount_usd:,.2f} ({tx.asset}) was not approved. Please contact support.")
    messages.warning(request, f"Transaction rejected for {tx.user.email}.")
    return redirect("panel:transaction_detail", pk=pk)

# ── Wallets ───────────────────────────────────────────────────────────────────

@superuser_required
def wallet_list(request):
    return render(request, "panel/wallets/list.html", {"wallets": AdminWallet.objects.all()})


@superuser_required
def wallet_create(request):
    form = AdminWalletForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Wallet added.")
        return redirect("panel:wallet_list")
    return render(request, "panel/wallets/form.html", {"form": form, "action": "Add"})


@superuser_required
def wallet_edit(request, pk):
    wallet = get_object_or_404(AdminWallet, pk=pk)
    form   = AdminWalletForm(request.POST or None, request.FILES or None, instance=wallet)
    if form.is_valid():
        form.save()
        messages.success(request, "Wallet updated.")
        return redirect("panel:wallet_list")
    return render(request, "panel/wallets/form.html", {"form": form, "action": "Edit", "obj": wallet})


@superuser_required
def wallet_delete(request, pk):
    wallet = get_object_or_404(AdminWallet, pk=pk)
    if request.method == "POST":
        wallet.delete()
        messages.success(request, "Wallet deleted.")
        return redirect("panel:wallet_list")
    return render(request, "panel/confirm_delete.html", {
        "title": "Delete wallet?",
        "subtitle": wallet.get_name_display(),
        "warning": "This wallet will no longer be available for deposits.",
        "cancel_url": "/panel/wallets/",
    })

# ── Copy Trades ───────────────────────────────────────────────────────────────

@superuser_required
def copy_trade_list(request):
    qs  = CopyRelationship.objects.select_related("copier", "trader").order_by("-started_at")
    sf  = request.GET.get("status", "")
    q   = request.GET.get("q", "").strip()
    if sf: qs = qs.filter(status=sf)
    if q:  qs = qs.filter(Q(copier__email__icontains=q) | Q(trader__name__icontains=q))
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "panel/copy_trades/list.html", {
        "page_obj": page, "q": q, "status_f": sf,
        "status_choices": CopyRelationship.STATUS_CHOICES,
    })


@superuser_required
@require_POST
def copy_trade_approve_cancel(request, pk):
    """Admin approves a cancel request — relationship is deleted."""
    rel = get_object_or_404(CopyRelationship, pk=pk, status="cancel_requested")
    user = rel.copier
    trader_name = rel.trader.name
    rel.delete()
    Notification.objects.create(
        user=user, notif_type="trade", title="Copy Cancelled",
        body=f"Your request to stop copying {trader_name} has been approved.",
    )
    messages.success(request, f"Cancel approved — {user.email} disconnected from {trader_name}.")
    return redirect(request.META.get("HTTP_REFERER", "panel:copy_trade_list"))


@superuser_required
@require_POST
def copy_trade_reject_cancel(request, pk):
    """Admin rejects a cancel request — relationship reverts to active."""
    rel = get_object_or_404(CopyRelationship, pk=pk, status="cancel_requested")
    rel.status = "active"
    rel.save(update_fields=["status"])
    Notification.objects.create(
        user=rel.copier, notif_type="trade", title="Cancel Request Rejected",
        body=f"Your request to stop copying {rel.trader.name} has been reviewed and rejected. You are still copying this trader.",
    )
    messages.warning(request, f"Cancel request rejected — {rel.copier.email} remains active on {rel.trader.name}.")
    return redirect(request.META.get("HTTP_REFERER", "panel:copy_trade_list"))


# ── Investors ─────────────────────────────────────────────────────────────────

@superuser_required
def investor_list(request):
    """Unique users who are copying at least one trader."""
    q = request.GET.get("q", "").strip()
    qs = User.objects.filter(copying__isnull=False).distinct().annotate(
        trader_count=Count("copying", distinct=True),
        active_count=Count("copying", filter=Q(copying__status="active"), distinct=True),
        cancel_count=Count("copying", filter=Q(copying__status="cancel_requested"), distinct=True),
    ).order_by("-date_joined")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
    page = Paginator(qs, 30).get_page(request.GET.get("page"))
    return render(request, "panel/investors/list.html", {"page_obj": page, "q": q})


@superuser_required
def investor_add_trade(request, user_pk):
    """Add a CopyTrade for a specific user."""
    user = get_object_or_404(User, pk=user_pk)
    form = CopyTradeForm(request.POST or None)
    if form.is_valid():
        trade = form.save(commit=False)
        trade.user = user
        trade.save()
        Notification.objects.create(
            user=user, notif_type="trade", title="New Trade",
            body=f"A new {trade.direction} {trade.trade_type} trade on {trade.asset} has been added to your copy portfolio.",
        )
        messages.success(request, f"Trade added for {user.email}.")
        return redirect("panel:investor_list")
    return render(request, "panel/investors/add_trade.html", {"form": form, "inv_user": user})


@superuser_required
def investor_bulk_add_trade(request):
    """Bulk add a trade to multiple selected users."""
    user_ids = request.POST.getlist("user_ids") or request.GET.getlist("user_ids")
    users = User.objects.filter(pk__in=user_ids) if user_ids else User.objects.none()

    if not user_ids:
        messages.error(request, "No investors selected.")
        return redirect("panel:investor_list")

    form = BulkCopyTradeForm(request.POST if request.method == "POST" and "asset" in request.POST else None)
    if form.is_valid():
        count = 0
        for user in users:
            CopyTrade.objects.create(
                user=user,
                asset=form.cleaned_data["asset"],
                trade_type=form.cleaned_data["trade_type"],
                direction=form.cleaned_data["direction"],
                price=form.cleaned_data["price"],
                pnl=form.cleaned_data["pnl"],
                status=form.cleaned_data["status"],
                category=form.cleaned_data["category"],
            )
            Notification.objects.create(
                user=user, notif_type="trade", title="New Trade",
                body=f"A new {form.cleaned_data['direction']} {form.cleaned_data['trade_type']} trade on {form.cleaned_data['asset']} has been added to your copy portfolio.",
            )
            count += 1
        messages.success(request, f"Trade added to {count} investor(s).")
        return redirect("panel:investor_list")

    return render(request, "panel/investors/bulk_add_trade.html", {
        "form": form,
        "users": users,
        "user_ids": user_ids,
    })


# ── Tags ──────────────────────────────────────────────────────────────────────

@superuser_required
def tag_list(request):
    tags = TraderTag.objects.annotate(trader_count=Count("traders")).order_by("name")
    return render(request, "panel/tags/list.html", {"tags": tags})


@superuser_required
def tag_create(request):
    form = TraderTagForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Tag created.")
        return redirect("panel:tag_list")
    return render(request, "panel/tags/form.html", {"form": form, "action": "Create"})


@superuser_required
def tag_edit(request, pk):
    tag  = get_object_or_404(TraderTag, pk=pk)
    form = TraderTagForm(request.POST or None, instance=tag)
    if form.is_valid():
        form.save()
        messages.success(request, f"Tag '{tag.name}' updated.")
        return redirect("panel:tag_list")
    return render(request, "panel/tags/form.html", {"form": form, "action": "Edit", "obj": tag})


@superuser_required
def tag_delete(request, pk):
    tag = get_object_or_404(TraderTag, pk=pk)
    if request.method == "POST":
        tag.delete()
        messages.success(request, f"Tag '{tag.name}' deleted.")
        return redirect("panel:tag_list")
    return render(request, "panel/confirm_delete.html", {
        "title": "Delete tag?",
        "subtitle": tag.name,
        "warning": "This tag will be removed from all traders.",
        "cancel_url": "/panel/tags/",
    })
