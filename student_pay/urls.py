"""
URL configuration for student_pay project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from django.http import HttpResponse, HttpResponseForbidden
import logging
import os


logger = logging.getLogger(__name__)


def ping_site(request):
    if request.headers.get("X-Cron-Token") != os.getenv("CRON_SECRET_TOKEN"):
        logger.warning(f"Unauthorized ping attempt from {request.META.get('REMOTE_ADDR')}")
        return HttpResponseForbidden("Forbidden")
    logger.info("Ping successful")
    return HttpResponse("Hello World")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("pay/", include("pay.urls")),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("ping/", ping_site, name="ping_site"),
]
