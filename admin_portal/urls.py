from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_portal_dashboard"),
    path(
        "api/statistics/",
        views.admin_statistics_api,
        name="admin_portal_statistics_api",
    ),
]
