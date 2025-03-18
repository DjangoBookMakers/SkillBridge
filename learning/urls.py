from django.urls import path
from . import views

app_name = "learning"

urlpatterns = [
    # 대시보드
    path("dashboard/", views.dashboard, name="dashboard"),
    # 이어서 학습하기
    path("course/<int:course_id>/resume/", views.resume_course, name="resume_course"),
    # # 현재 강의 다음의 학습 항목으로 이동
    path("lecture/<int:lecture_id>/next/", views.next_item, name="next_item"),
    # 강의 시청 및 미션
    path("lecture/video/<int:lecture_id>/", views.video_lecture, name="video_lecture"),
    path("lecture/mission/<int:lecture_id>/", views.mission, name="mission"),
    path(
        "mission/result/<int:attempt_id>/", views.mission_result, name="mission_result"
    ),
    # 프로젝트 제출
    path(
        "subject/<int:subject_id>/project/submit/",
        views.submit_project,
        name="submit_project",
    ),
    path("project/<int:submission_id>/", views.project_detail, name="project_detail"),
    # 수료증
    path(
        "enrollment/<int:enrollment_id>/certificate/issue/",
        views.issue_certificate,
        name="issue_certificate",
    ),
    path(
        "certificate/<int:certificate_id>/",
        views.view_certificate,
        name="view_certificate",
    ),
    path(
        "certificate/<int:certificate_id>/download/",
        views.download_certificate,
        name="download_certificate",
    ),
]
