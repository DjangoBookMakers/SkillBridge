from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("social/", include("allauth.urls")),
    path("accounts/", include("accounts.urls")),
    path("admin-portal/", include("admin_portal.urls")),
    path("courses/", include("courses.urls")),
    path("learning/", include("learning.urls")),
    path("payments/", include("payments.urls")),
    path("", lambda request: redirect("courses/")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
