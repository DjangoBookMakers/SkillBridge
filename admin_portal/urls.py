from django.urls import path
from . import views

app_name = "admin_portal"

urlpatterns = [
    path("dashboard/", views.admin_dashboard, name="dashboard"),
    path(
        "api/statistics/",
        views.admin_statistics_api,
        name="statistics_api",
    ),
    path("projects/", views.admin_pending_projects, name="pending_projects"),
    path(
        "projects/<int:project_id>/",
        views.project_detail,
        name="project_detail",
    ),
    path(
        "projects/<int:project_id>/evaluate/",
        views.evaluate_project,
        name="evaluate_project",
    ),
    # 과정 진행 상황 모니터링 관련
    path(
        "courses/progress/",
        views.course_progress_overview,
        name="course_progress",
    ),
    path(
        "courses/<int:course_id>/progress/",
        views.course_progress_detail,
        name="course_progress_detail",
    ),
    path(
        "courses/<int:course_id>/attendance/",
        views.course_attendance,
        name="course_attendance",
    ),
    path(
        "courses/<int:course_id>/attendance/pdf/",
        views.course_attendance_pdf,
        name="course_attendance_pdf",
    ),
    path("courses/", views.course_management, name="course_management"),
    path("courses/create/", views.course_create, name="course_create"),
    path(
        "courses/<int:course_id>/",
        views.course_detail,
        name="course_detail",
    ),
    path(
        "courses/<int:course_id>/delete/",
        views.course_delete,
        name="course_delete",
    ),
    # 과목 관리 URL
    path(
        "courses/<int:course_id>/subjects/",
        views.subject_management,
        name="subject_management",
    ),
    path(
        "courses/<int:course_id>/subjects/create/",
        views.subject_create,
        name="subject_create",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/",
        views.subject_detail,
        name="subject_detail",
    ),
    # 강의 관리 URL
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/",
        views.lecture_management,
        name="lecture_management",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/create/",
        views.lecture_create,
        name="lecture_create",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/",
        views.lecture_detail,
        name="lecture_detail",
    ),
    # 사용자 학습 기록 관련
    path(
        "users/learning-records/",
        views.user_learning_records,
        name="user_learning_records",
    ),
    path("payments/", views.payment_management, name="payments"),
    path(
        "payments/<int:payment_id>/",
        views.payment_detail_admin,
        name="payment_detail",
    ),
    path(
        "enrollments/manage/",
        views.manage_student_enrollment,
        name="manage_enrollment",
    ),
]
