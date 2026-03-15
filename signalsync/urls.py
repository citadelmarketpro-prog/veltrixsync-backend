from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
from core.urls import dashboard_urlpatterns, trader_urlpatterns, transaction_urlpatterns

urlpatterns = [
    path("",                     RedirectView.as_view(url="/panel/", permanent=False)),
    path("admin/",              admin.site.urls),
    path("api/auth/",           include("core.urls")),
    path("api/transactions/",   include(transaction_urlpatterns)),
    path("api/dashboard/",      include(dashboard_urlpatterns)),
    path("api/traders/",        include(trader_urlpatterns)),
    path("panel/",              include("dashboard.urls", namespace="panel")),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
