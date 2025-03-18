from django.urls import path
from . import views

app_name = "admin_portal"

urlpatterns = [
    # 관리자 대시보드 메인화면 관련
    path("dashboard/", views.AdminDashboardView.as_view(), name="dashboard"),
    path(
        "api/statistics/",
        views.AdminStatisticsAPIView.as_view(),
        name="statistics_api",
    ),
    # 프로젝트 관련
    path("projects/", views.PendingProjectsListView.as_view(), name="pending_projects"),
    path(
        "projects/<int:project_id>/",
        views.ProjectDetailView.as_view(),
        name="project_detail",
    ),
    path(
        "projects/<int:project_id>/evaluate/",
        views.EvaluateProjectView.as_view(),
        name="evaluate_project",
    ),
    # 과정 진행 상황 모니터링 관련
    path(
        "courses/progress/",
        views.CourseProgressOverviewView.as_view(),
        name="course_progress",
    ),
    path(
        "courses/<int:course_id>/progress/",
        views.CourseProgressDetailView.as_view(),
        name="course_progress_detail",
    ),
    path(
        "courses/<int:course_id>/attendance/",
        views.CourseAttendanceView.as_view(),
        name="course_attendance",
    ),
    path(
        "courses/<int:course_id>/attendance/pdf/",
        views.CourseAttendancePDFView.as_view(),
        name="course_attendance_pdf",
    ),
    # 과정 관리 관련
    path("courses/", views.CourseManagementView.as_view(), name="course_management"),
    path("courses/create/", views.CourseCreateView.as_view(), name="course_create"),
    path(
        "courses/<int:course_id>/",
        views.CourseDetailView.as_view(),
        name="course_detail",
    ),
    path(
        "courses/<int:course_id>/delete/",
        views.CourseDeleteView.as_view(),
        name="course_delete",
    ),
    # 과목 관리 관련
    path(
        "courses/<int:course_id>/subjects/",
        views.SubjectManagementView.as_view(),
        name="subject_management",
    ),
    path(
        "courses/<int:course_id>/subjects/create/",
        views.SubjectCreateView.as_view(),
        name="subject_create",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/",
        views.SubjectDetailView.as_view(),
        name="subject_detail",
    ),
    # 강의 관리 관련
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/",
        views.LectureManagementView.as_view(),
        name="lecture_management",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/create/",
        views.LectureCreateView.as_view(),
        name="lecture_create",
    ),
    path(
        "courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/",
        views.LectureDetailView.as_view(),
        name="lecture_detail",
    ),
    # 사용자 학습 기록 관련
    path(
        "users/learning-records/",
        views.UserLearningRecordsView.as_view(),
        name="user_learning_records",
    ),
    # 결제 관련
    path("payments/", views.PaymentManagementView.as_view(), name="payments"),
    path(
        "payments/<int:payment_id>/",
        views.PaymentDetailAdminView.as_view(),
        name="payment_detail",
    ),
    path(
        "enrollments/manage/",
        views.ManageStudentEnrollmentView.as_view(),
        name="manage_enrollment",
    ),
]
