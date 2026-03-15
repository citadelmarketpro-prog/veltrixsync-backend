from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .authentication import CookieJWTAuthentication
from .email_service import (
    send_password_changed_email,
    send_password_reset_email,
    send_welcome_email,
)
from .models import (
    AdminWallet,
    CopyRelationship,
    CopyTrade,
    Notification,
    Trader,
    TradeHistory,
    TraderPosition,
    TraderSection,
    Transaction,
)
from .serializers import (
    AdminWalletSerializer,
    ChangePasswordSerializer,
    CopyingTraderSerializer,
    CopyRelationshipSerializer,
    CopyTradeSerializer,
    DepositSerializer,
    ForgotPasswordSerializer,
    KycSerializer,
    LoginSerializer,
    NotificationSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    TradeHistorySerializer,
    TraderDetailSerializer,
    TraderPositionSerializer,
    TraderSerializer,
    TransactionSerializer,
    UpdateProfileSerializer,
    UserProfileSerializer,
    WithdrawalSerializer,
)

User = get_user_model()

# ─────────────────────────────────────────────────────────────────────────────
# Cookie helpers
# ─────────────────────────────────────────────────────────────────────────────

from decouple import config as _env_config

COOKIE_SECURE   = _env_config("COOKIE_SECURE",   default=not settings.DEBUG, cast=bool)
COOKIE_SAMESITE = _env_config("COOKIE_SAMESITE", default="Lax")
ACCESS_MAX_AGE  = 60 * 15                     # 15 minutes
REFRESH_MAX_AGE = 60 * 60 * 24 * 7           # 7 days


def _set_auth_cookies(response: Response, refresh: RefreshToken) -> None:
    """Write access + refresh tokens into HTTP-only cookies."""
    response.set_cookie(
        key="access_token",
        value=str(refresh.access_token),
        max_age=ACCESS_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=str(refresh),
        max_age=REFRESH_MAX_AGE,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie("access_token",  path="/")
    response.delete_cookie("refresh_token", path="/")


# ─────────────────────────────────────────────────────────────────────────────
# Auth views
# ─────────────────────────────────────────────────────────────────────────────

class RegisterView(APIView):
    """POST /api/auth/register/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh  = RefreshToken.for_user(user)
        send_welcome_email(user)          # fire-and-forget (logged on failure)
        response = Response(
            {"detail": "Account created successfully."},
            status=status.HTTP_201_CREATED,
        )
        _set_auth_cookies(response, refresh)
        return response


class LoginView(APIView):
    """POST /api/auth/login/"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            request,
            email=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if user is None:
            return Response(
                {"detail": "Invalid email or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        if not user.is_active:
            return Response(
                {"detail": "This account has been disabled."},
                status=status.HTTP_403_FORBIDDEN,
            )

        refresh  = RefreshToken.for_user(user)
        response = Response({"detail": "Login successful."})
        _set_auth_cookies(response, refresh)
        return response


class LogoutView(APIView):
    """POST /api/auth/logout/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        response    = Response({"detail": "Logged out successfully."})
        _clear_auth_cookies(response)

        if raw_refresh:
            try:
                RefreshToken(raw_refresh).blacklist()
            except TokenError:
                pass  # already expired or invalid

        return response


class TokenRefreshView(APIView):
    """POST /api/auth/token/refresh/"""
    permission_classes = [AllowAny]

    def post(self, request):
        raw_refresh = request.COOKIES.get("refresh_token")
        if not raw_refresh:
            return Response(
                {"detail": "Refresh token not found."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        try:
            refresh  = RefreshToken(raw_refresh)
            response = Response({"detail": "Token refreshed."})
            _set_auth_cookies(response, refresh)
            return response
        except TokenError as e:
            return Response({"detail": str(e)}, status=status.HTTP_401_UNAUTHORIZED)


class MeView(APIView):
    """GET / PATCH /api/auth/me/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(
            request.user, context={"request": request}
        )
        return Response(serializer.data)

    def patch(self, request):
        serializer = UpdateProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            UserProfileSerializer(request.user, context={"request": request}).data
        )


# ─────────────────────────────────────────────────────────────────────────────
# Password views
# ─────────────────────────────────────────────────────────────────────────────

class ForgotPasswordView(APIView):
    """
    POST /api/auth/password/forgot/
    Body: { "email": "user@example.com" }

    Always returns 200 to prevent email enumeration.
    If the email exists a password-reset token is generated.
    In production you would send this token via email; here we return it
    in the response so the frontend can pass it straight to ResetPasswordView
    (swap for an email task once SMTP is configured).
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data["email"]
        try:
            user  = User.objects.get(email=email)
            uid   = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            send_password_reset_email(user, token=token, uid=uid)
        except User.DoesNotExist:
            pass  # do not reveal whether the email exists

        # Always the same response to prevent email enumeration
        return Response(
            {"detail": "If that email is registered you will receive reset instructions shortly."},
            status=status.HTTP_200_OK,
        )


class ResetPasswordView(APIView):
    """
    POST /api/auth/password/reset/
    Body: { "uid": "...", "token": "...", "password": "...", "password2": "..." }
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            pk   = force_str(urlsafe_base64_decode(serializer.validated_data["uid"]))
            user = User.objects.get(pk=pk)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response(
                {"detail": "Invalid reset link."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not default_token_generator.check_token(user, serializer.validated_data["token"]):
            return Response(
                {"detail": "Reset link has expired or is invalid."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["password"])
        user.save()
        return Response({"detail": "Password has been reset successfully."})


class ChangePasswordView(APIView):
    """
    POST /api/auth/password/change/
    Requires authentication. Body: { "old_password", "password", "password2" }
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"detail": "Current password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data["password"])
        request.user.save()
        send_password_changed_email(request.user)   # notify user of change

        # Rotate tokens so existing sessions are invalidated
        refresh  = RefreshToken.for_user(request.user)
        response = Response({"detail": "Password changed successfully."})
        _set_auth_cookies(response, refresh)
        return response


# ─────────────────────────────────────────────────────────────────────────────
# KYC view
# ─────────────────────────────────────────────────────────────────────────────

class KycView(APIView):
    """
    GET  /api/auth/kyc/  — return current KYC data for the logged-in user
    PATCH /api/auth/kyc/ — submit / update KYC data (multipart for file uploads)
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        serializer = KycSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    def patch(self, request):
        from django.utils import timezone as tz
        serializer = KycSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)

        # Mark as submitted when the user first sends KYC data
        user = request.user
        if user.kyc_status == "not_submitted":
            serializer.save(kyc_status="submitted", kyc_submitted_at=tz.now())
        else:
            serializer.save()

        return Response(
            KycSerializer(request.user, context={"request": request}).data
        )


# ─────────────────────────────────────────────────────────────────────────────
# Notification views
# ─────────────────────────────────────────────────────────────────────────────

class NotificationListView(APIView):
    """
    GET  /api/notifications/          — return paginated list for the logged-in user
    POST /api/notifications/read-all/ — mark every notification as read
    """
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)
        serializer = NotificationSerializer(qs, many=True)
        unread_count = qs.filter(is_read=False).count()
        return Response({
            "results":      serializer.data,
            "unread_count": unread_count,
        })


class NotificationReadAllView(APIView):
    """POST /api/notifications/read-all/ — mark all as read."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return Response({"detail": "All notifications marked as read."})


class NotificationDetailView(APIView):
    """PATCH /api/notifications/<pk>/ — mark a single notification as read."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def patch(self, request, pk):
        try:
            notif = Notification.objects.get(pk=pk, user=request.user)
        except Notification.DoesNotExist:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        notif.is_read = True
        notif.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notif).data)


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────

class TransactionListView(APIView):
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        qs = Transaction.objects.filter(user=request.user)

        tx_type = request.query_params.get("type", "").lower()
        asset   = request.query_params.get("asset", "").strip()
        start   = request.query_params.get("start", "").strip()
        end     = request.query_params.get("end", "").strip()

        if tx_type and tx_type != "all":
            qs = qs.filter(tx_type=tx_type)
        if asset:
            qs = qs.filter(asset__icontains=asset)
        if start:
            qs = qs.filter(created_at__date__gte=start)
        if end:
            qs = qs.filter(created_at__date__lte=end)

        page      = max(1, int(request.query_params.get("page", 1)))
        page_size = max(1, min(100, int(request.query_params.get("page_size", 10))))
        total     = qs.count()

        results = qs[(page - 1) * page_size : page * page_size]
        serializer = TransactionSerializer(results, many=True)

        return Response({
            "results":     serializer.data,
            "total":       total,
            "page":        page,
            "page_size":   page_size,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard stats
# ─────────────────────────────────────────────────────────────────────────────

class DashboardStatsView(APIView):
    """GET /api/dashboard/stats/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum
        from django.utils import timezone
        from decimal import Decimal

        user = request.user

        # Available balance and profit come straight from the user model
        balance = user.balance or Decimal("0")
        profit  = user.profit  or Decimal("0")
        portfolio = balance + profit

        # Invested value = cumulative completed deposits
        invested = Transaction.objects.filter(
            user=user, tx_type="deposit", status="completed"
        ).aggregate(total=Sum("amount_usd"))["total"] or Decimal("0")

        # Last-month deposits (completed)
        now = timezone.now()
        if now.month == 1:
            lm_year, lm_month = now.year - 1, 12
        else:
            lm_year, lm_month = now.year, now.month - 1

        last_month_deposits = Transaction.objects.filter(
            user=user,
            tx_type="deposit",
            status="completed",
            created_at__year=lm_year,
            created_at__month=lm_month,
        ).aggregate(total=Sum("amount_usd"))["total"] or Decimal("0")

        # Percentage change vs last month's deposits
        if last_month_deposits > 0:
            pct_change = float((balance - last_month_deposits) / last_month_deposits * 100)
        else:
            pct_change = 0.0

        return Response({
            "balance":             float(balance),
            "profit":              float(profit),
            "portfolio":           float(portfolio),
            "invested_value":      float(invested),
            "last_month_deposits": float(last_month_deposits),
            "pct_change":          round(pct_change, 2),
        })


# ─────────────────────────────────────────────────────────────────────────────
# Admin wallets list (for deposit/withdrawal dropdowns)
# ─────────────────────────────────────────────────────────────────────────────

class AdminWalletListView(APIView):
    """GET /api/transactions/wallets/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, _request):
        wallets = AdminWallet.objects.filter(is_active=True)
        return Response(AdminWalletSerializer(wallets, many=True).data)


# ─────────────────────────────────────────────────────────────────────────────
# Deposit
# ─────────────────────────────────────────────────────────────────────────────

class DepositView(APIView):
    """POST /api/transactions/deposit/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet     = AdminWallet.objects.get(pk=serializer.validated_data["wallet_id"])
        amount_usd = serializer.validated_data["amount_usd"]

        tx = Transaction.objects.create(
            user=request.user,
            tx_type="deposit",
            asset=wallet.symbol,
            units=amount_usd,         # 1:1 for deposits (no conversion fee)
            amount_usd=amount_usd,
            status="pending",
        )
        return Response(
            {"detail": "Deposit request submitted.", "tx_id": str(tx.tx_id)},
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Withdrawal
# ─────────────────────────────────────────────────────────────────────────────

class WithdrawalView(APIView):
    """POST /api/transactions/withdraw/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request):
        from decimal import Decimal

        serializer = WithdrawalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        wallet        = AdminWallet.objects.get(pk=serializer.validated_data["wallet_id"])
        amount_usd    = serializer.validated_data["amount_usd"]
        withdraw_from = serializer.validated_data["withdraw_from"]   # "balance" | "profit"
        wallet_address = serializer.validated_data["wallet_address"]

        user = request.user
        available = user.balance if withdraw_from == "balance" else user.profit
        available  = available or Decimal("0")

        if available < amount_usd:
            source_label = "Available Balance" if withdraw_from == "balance" else "Profit (ROI)"
            return Response(
                {"detail": f"You have insufficient funds in your {source_label}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Reserve the funds immediately
        if withdraw_from == "balance":
            user.balance = available - amount_usd
        else:
            user.profit = available - amount_usd
        user.save(update_fields=["balance" if withdraw_from == "balance" else "profit"])

        tx = Transaction.objects.create(
            user=request.user,
            tx_type="withdrawal",
            asset=wallet.symbol,
            units=amount_usd,
            amount_usd=amount_usd,
            wallet_address=wallet_address,
            status="pending",
        )
        return Response(
            {"detail": "Withdrawal request submitted.", "tx_id": str(tx.tx_id)},
            status=status.HTTP_201_CREATED,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Trader public listing / detail
# ─────────────────────────────────────────────────────────────────────────────

class TraderListView(APIView):
    """GET /api/traders/?search=<query>"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q
        search = request.query_params.get("search", "").strip()

        if search:
            qs = Trader.objects.filter(
                Q(name__icontains=search)     |
                Q(specialty__icontains=search) |
                Q(trader_tags__name__icontains=search)
            ).distinct()
            return Response({"search_results": TraderSerializer(qs, many=True).data})

        sections = ["trending", "rising_stars", "most_copied", "reliable", "proven"]
        result = {}
        for section in sections:
            memberships = (
                TraderSection.objects
                .filter(section=section)
                .select_related("trader")
                .order_by("rank")
            )
            traders = []
            for m in memberships:
                t = m.trader
                t._section_rank = m.rank
                traders.append(t)
            result[section] = TraderSerializer(traders, many=True).data

        return Response(result)


class TraderDetailView(APIView):
    """GET /api/traders/<pk>/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        try:
            trader = Trader.objects.get(pk=pk)
        except Trader.DoesNotExist:
            return Response({"detail": "Trader not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(TraderDetailSerializer(trader, context={"request": request}).data)


class CopyTraderView(APIView):
    """POST /api/traders/<pk>/copy/  -- start copying
       DELETE /api/traders/<pk>/copy/ -- cancel copying"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def post(self, request, pk):
        try:
            trader = Trader.objects.get(pk=pk)
        except Trader.DoesNotExist:
            return Response({"detail": "Trader not found."}, status=status.HTTP_404_NOT_FOUND)

        funds = request.user.balance + request.user.profit
        if funds < trader.min_capital:
            return Response(
                {"detail": "Insufficient balance to copy this trader."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        CopyRelationship.objects.get_or_create(
            copier=request.user,
            trader=trader,
            defaults={"allocated_amount": trader.min_capital},
        )
        return Response({"status": "copying"})

    def delete(self, request, pk):
        try:
            trader = Trader.objects.get(pk=pk)
        except Trader.DoesNotExist:
            return Response({"detail": "Trader not found."}, status=status.HTTP_404_NOT_FOUND)

        rel = CopyRelationship.objects.filter(copier=request.user, trader=trader, status="active").first()
        if not rel:
            return Response({"detail": "Not currently copying this trader."}, status=status.HTTP_400_BAD_REQUEST)

        rel.status = "cancel_requested"
        rel.save(update_fields=["status"])
        return Response({"status": "cancel_requested"})


class TraderPositionListView(APIView):
    """GET /api/traders/<pk>/positions/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        positions = TraderPosition.objects.filter(trader_id=pk)
        return Response(TraderPositionSerializer(positions, many=True).data)


class TraderHistoryListView(APIView):
    """GET /api/traders/<pk>/history/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        history = TradeHistory.objects.filter(trader_id=pk)
        return Response(TradeHistorySerializer(history, many=True).data)


class TraderCopierListView(APIView):
    """GET /api/traders/<pk>/copiers/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        copiers = CopyRelationship.objects.filter(trader_id=pk).select_related("copier")
        return Response(CopyRelationshipSerializer(copiers, many=True).data)


class TraderSimilarListView(APIView):
    """GET /api/traders/<pk>/similar/"""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request, pk):
        try:
            trader = Trader.objects.get(pk=pk)
        except Trader.DoesNotExist:
            return Response({"detail": "Trader not found."}, status=status.HTTP_404_NOT_FOUND)
        similar = Trader.objects.filter(
            market_category=trader.market_category,
        ).exclude(pk=pk)[:8]
        return Response(TraderSerializer(similar, many=True).data)


class CopyTradeListView(APIView):
    """GET /api/copy-trades/ -- trades and actively-copied traders for the logged-in user."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        trades   = CopyTrade.objects.filter(user=request.user).select_related("trader")
        copying  = CopyRelationship.objects.filter(
            copier=request.user, status="active"
        ).select_related("trader")
        return Response({
            "trades":  CopyTradeSerializer(trades, many=True).data,
            "copying": CopyingTraderSerializer(copying, many=True).data,
        })


class PortfolioBreakdownView(APIView):
    """GET /api/dashboard/portfolio-breakdown/ -- portfolio breakdown by category + growth %."""
    authentication_classes = [CookieJWTAuthentication]
    permission_classes     = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Sum, Count
        from django.utils import timezone
        from datetime import timedelta
        from decimal import Decimal

        user = request.user
        now  = timezone.now()

        # Growth: compare this month's total PNL vs last month's
        last_month_date = now - timedelta(days=32)
        this_month_pnl = CopyTrade.objects.filter(
            user=user,
            created_at__year=now.year,
            created_at__month=now.month,
        ).aggregate(s=Sum("pnl"))["s"] or Decimal("0")

        last_month_pnl = CopyTrade.objects.filter(
            user=user,
            created_at__year=last_month_date.year,
            created_at__month=last_month_date.month,
        ).aggregate(s=Sum("pnl"))["s"] or Decimal("0")

        if last_month_pnl != 0:
            growth_pct = float((this_month_pnl - last_month_pnl) / abs(last_month_pnl) * 100)
        elif this_month_pnl > 0:
            growth_pct = 100.0
        else:
            growth_pct = 0.0

        # Breakdown by category (exclude categories with 0 trades)
        cat_rows = (
            CopyTrade.objects
            .filter(user=user)
            .values("category")
            .annotate(total_pnl=Sum("pnl"), count=Count("id"))
            .order_by("-total_pnl")
        )

        CATEGORY_META = {
            "stocks":      {"label": "Stocks",      "legend_color": "#9ab4a2", "base_color": "#8aaa96", "line_color": "#a8c4b0"},
            "forex":       {"label": "Forex",       "legend_color": "#4a7862", "base_color": "#3d6852", "line_color": "#527c66"},
            "commodities": {"label": "Commodities", "legend_color": "#133c26", "base_color": "#0e3020", "line_color": "#1a4a30"},
            "crypto":      {"label": "Crypto",      "legend_color": "#2a5c3a", "base_color": "#1a4a2e", "line_color": "#2a6a40"},
        }

        total_abs = sum(abs(float(r["total_pnl"] or 0)) for r in cat_rows)

        breakdown = []
        for row in cat_rows:
            pnl_val = float(row["total_pnl"] or 0)
            pct     = round(abs(pnl_val) / total_abs * 100, 1) if total_abs > 0 else 0
            meta    = CATEGORY_META.get(row["category"], {
                "label": row["category"].title(), "legend_color": "#6a8a7a",
                "base_color": "#4a6a5a", "line_color": "#6a8a7a",
            })
            breakdown.append({
                "category":     row["category"],
                "label":        meta["label"],
                "legend_color": meta["legend_color"],
                "base_color":   meta["base_color"],
                "line_color":   meta["line_color"],
                "pnl":          str(round(pnl_val, 2)),
                "pct":          pct,
                "count":        row["count"],
            })

        return Response({
            "growth_pct": round(growth_pct, 1),
            "breakdown":  breakdown,
        })











