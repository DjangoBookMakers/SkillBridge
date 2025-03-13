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
    # 과정 진행 상황 모니터링 관련
    path(
        "courses/progress/",
        views.course_progress_overview,
        name="admin_portal_course_progress",
    ),
    path(
        "courses/<int:course_id>/progress/",
        views.course_progress_detail,
        name="admin_portal_course_progress_detail",
    ),
    path(
        "courses/<int:course_id>/attendance/",
        views.course_attendance,
        name="admin_portal_course_attendance",
    ),
    path(
        "courses/<int:course_id>/attendance/pdf/",
        views.course_attendance_pdf,
        name="admin_portal_course_attendance_pdf",
    ),
]
