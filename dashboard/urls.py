from django.urls import path
from . import views

app_name = "panel"

urlpatterns = [
    # Auth
    path("login/",   views.panel_login,  name="login"),
    path("logout/",  views.panel_logout, name="logout"),

    # Dashboard
    path("",         views.dashboard_home, name="dashboard"),

    # Users
    path("users/",                              views.user_list,        name="user_list"),
    path("users/create/",                       views.user_create,      name="user_create"),
    path("users/<int:pk>/",                     views.user_detail,      name="user_detail"),
    path("users/<int:pk>/edit/",                views.user_edit,        name="user_edit"),
    path("users/<int:pk>/delete/",              views.user_delete,      name="user_delete"),
    path("users/<int:pk>/approve-kyc/",         views.user_approve_kyc, name="user_approve_kyc"),
    path("users/<int:pk>/reject-kyc/",          views.user_reject_kyc,  name="user_reject_kyc"),
    path("users/<int:pk>/adjust-funds/",        views.user_adjust_funds,name="user_adjust_funds"),

    # Traders
    path("traders/",                                           views.trader_list,             name="trader_list"),
    path("traders/create/",                                    views.trader_create,           name="trader_create"),
    path("traders/<int:pk>/",                                  views.trader_detail,           name="trader_detail"),
    path("traders/<int:pk>/edit/",                             views.trader_edit,             name="trader_edit"),
    path("traders/<int:pk>/delete/",                           views.trader_delete,           name="trader_delete"),
    path("traders/<int:pk>/copiers/<int:copier_pk>/disconnect/", views.trader_disconnect_copier, name="trader_disconnect_copier"),
    path("traders/<int:pk>/sections/add/",                     views.trader_add_section,      name="trader_add_section"),
    path("traders/<int:pk>/sections/<int:section_pk>/remove/", views.trader_remove_section,   name="trader_remove_section"),
    path("traders/<int:pk>/assets/add/",                       views.trader_add_asset,        name="trader_add_asset"),
    path("traders/<int:pk>/assets/<int:asset_pk>/edit/",       views.trader_edit_asset,       name="trader_edit_asset"),
    path("traders/<int:pk>/assets/<int:asset_pk>/delete/",     views.trader_delete_asset,     name="trader_delete_asset"),
    path("traders/<int:pk>/allocations/add/",                  views.trader_add_allocation,   name="trader_add_allocation"),
    path("traders/<int:pk>/allocations/<int:alloc_pk>/edit/",  views.trader_edit_allocation,  name="trader_edit_allocation"),
    path("traders/<int:pk>/allocations/<int:alloc_pk>/delete/",views.trader_delete_allocation,name="trader_delete_allocation"),
    path("traders/<int:pk>/positions/add/",                    views.trader_add_position,     name="trader_add_position"),
    path("traders/<int:pk>/positions/<int:pos_pk>/edit/",      views.trader_edit_position,    name="trader_edit_position"),
    path("traders/<int:pk>/positions/<int:pos_pk>/delete/",    views.trader_delete_position,  name="trader_delete_position"),
    path("traders/<int:pk>/history/add/",                      views.trader_add_history,      name="trader_add_history"),
    path("traders/<int:pk>/history/<int:hist_pk>/edit/",       views.trader_edit_history,     name="trader_edit_history"),
    path("traders/<int:pk>/history/<int:hist_pk>/delete/",     views.trader_delete_history,   name="trader_delete_history"),

    # Transactions
    path("transactions/",                views.transaction_list,    name="transaction_list"),
    path("transactions/<int:pk>/",       views.transaction_detail,  name="transaction_detail"),
    path("transactions/<int:pk>/approve/", views.transaction_approve, name="transaction_approve"),
    path("transactions/<int:pk>/reject/",  views.transaction_reject,  name="transaction_reject"),

    # Wallets
    path("wallets/",                views.wallet_list,   name="wallet_list"),
    path("wallets/create/",         views.wallet_create, name="wallet_create"),
    path("wallets/<int:pk>/edit/",  views.wallet_edit,   name="wallet_edit"),
    path("wallets/<int:pk>/delete/",views.wallet_delete, name="wallet_delete"),

    # Tags
    path("tags/",                views.tag_list,   name="tag_list"),
    path("tags/create/",         views.tag_create, name="tag_create"),
    path("tags/<int:pk>/edit/",  views.tag_edit,   name="tag_edit"),
    path("tags/<int:pk>/delete/",views.tag_delete, name="tag_delete"),

    # Copy Trades
    path("copy-trades/",                                  views.copy_trade_list,          name="copy_trade_list"),
    path("copy-trades/<int:pk>/approve-cancel/",          views.copy_trade_approve_cancel, name="copy_trade_approve_cancel"),
    path("copy-trades/<int:pk>/reject-cancel/",           views.copy_trade_reject_cancel,  name="copy_trade_reject_cancel"),

    # Investors
    path("investors/",                               views.investor_list,           name="investor_list"),
    path("investors/<int:user_pk>/add-trade/",       views.investor_add_trade,      name="investor_add_trade"),
    path("investors/bulk-add-trade/",                views.investor_bulk_add_trade, name="investor_bulk_add_trade"),
]
