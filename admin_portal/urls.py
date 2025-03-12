from django.urls import path
from . import views

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="admin_portal_dashboard"),
    path(
        "api/statistics/",
        views.admin_statistics_api,
        name="admin_portal_statistics_api",
    ),
    path(
        "projects/", views.admin_pending_projects, name="admin_portal_pending_projects"
    ),
    path(
        "projects/<int:project_id>/",
        views.project_detail,
        name="admin_portal_project_detail",
    ),
    path(
        "projects/<int:project_id>/evaluate/",
        views.evaluate_project,
        name="admin_portal_evaluate_project",
    ),
]
