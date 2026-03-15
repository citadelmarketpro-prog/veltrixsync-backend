from django.urls import path
from .views import (
    AdminWalletListView,
    ChangePasswordView,
    CopyTradeListView,
    DashboardStatsView,
    PortfolioBreakdownView,
    DepositView,
    ForgotPasswordView,
    KycView,
    LoginView,
    LogoutView,
    MeView,
    NotificationDetailView,
    NotificationListView,
    NotificationReadAllView,
    RegisterView,
    ResetPasswordView,
    TokenRefreshView,
    CopyTraderView,
    TraderCopierListView,
    TraderDetailView,
    TraderHistoryListView,
    TraderListView,
    TraderPositionListView,
    TraderSimilarListView,
    TransactionListView,
    WithdrawalView,
)

urlpatterns = [
    path("register/",          RegisterView.as_view(),       name="auth-register"),
    path("login/",             LoginView.as_view(),           name="auth-login"),
    path("logout/",            LogoutView.as_view(),          name="auth-logout"),
    path("token/refresh/",     TokenRefreshView.as_view(),    name="auth-token-refresh"),
    path("me/",                MeView.as_view(),               name="auth-me"),
    path("kyc/",               KycView.as_view(),              name="auth-kyc"),
    path("password/forgot/",   ForgotPasswordView.as_view(),  name="auth-password-forgot"),
    path("password/reset/",    ResetPasswordView.as_view(),   name="auth-password-reset"),
    path("password/change/",   ChangePasswordView.as_view(),  name="auth-password-change"),

    # Notifications
    path("notifications/",           NotificationListView.as_view(),    name="notifications-list"),
    path("notifications/read-all/",  NotificationReadAllView.as_view(), name="notifications-read-all"),
    path("notifications/<int:pk>/",  NotificationDetailView.as_view(),  name="notifications-detail"),
]

# Transaction URLs — registered at /api/transactions/ in main urls.py
transaction_urlpatterns = [
    path("",           TransactionListView.as_view(),  name="transactions-list"),
    path("wallets/",   AdminWalletListView.as_view(),  name="transactions-wallets"),
    path("deposit/",   DepositView.as_view(),          name="transactions-deposit"),
    path("withdraw/",  WithdrawalView.as_view(),       name="transactions-withdraw"),
]

# Dashboard URLs — registered at /api/dashboard/ in main urls.py
dashboard_urlpatterns = [
    path("stats/",                DashboardStatsView.as_view(),       name="dashboard-stats"),
    path("copy-trades/",          CopyTradeListView.as_view(),         name="dashboard-copy-trades"),
    path("portfolio-breakdown/",  PortfolioBreakdownView.as_view(),    name="dashboard-portfolio-breakdown"),
]

# Trader URLs — registered at /api/traders/ in main urls.py
trader_urlpatterns = [
    path("",                    TraderListView.as_view(),         name="traders-list"),
    path("<int:pk>/",           TraderDetailView.as_view(),       name="traders-detail"),
    path("<int:pk>/positions/", TraderPositionListView.as_view(), name="traders-positions"),
    path("<int:pk>/history/",   TraderHistoryListView.as_view(),  name="traders-history"),
    path("<int:pk>/copiers/",   TraderCopierListView.as_view(),   name="traders-copiers"),
    path("<int:pk>/similar/",   TraderSimilarListView.as_view(),  name="traders-similar"),
    path("<int:pk>/copy/",      CopyTraderView.as_view(),         name="traders-copy"),
]
