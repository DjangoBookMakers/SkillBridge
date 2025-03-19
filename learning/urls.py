from django.urls import path
from . import views

app_name = "learning"

urlpatterns = [
    # 학습 대시보드 - 진행 중인 강의와 완료된 강의, 수료증 정보 확인
    path("dashboard/", views.DashboardView.as_view(), name="dashboard"),
    # 이어서 학습하기 - 현재 수강 중인 과정의 다음 학습 항목으로 이동
    path(
        "course/<int:course_id>/resume/",
        views.ResumeCourseView.as_view(),
        name="resume_course",
    ),
    # 다음 학습 항목으로 이동 - 현재 강의 이후의 학습 콘텐츠로 이동
    path(
        "lecture/<int:lecture_id>/next/", views.NextItemView.as_view(), name="next_item"
    ),
    # 동영상 강의 시청 페이지 - 비디오 콘텐츠와 관련 Q&A 표시
    path(
        "lecture/video/<int:lecture_id>/",
        views.VideoLectureView.as_view(),
        name="video_lecture",
    ),
    # 미션(퀴즈) 페이지 - 강의 관련 퀴즈 문제 풀기
    path(
        "lecture/mission/<int:lecture_id>/", views.MissionView.as_view(), name="mission"
    ),
    # 미션 결과 확인 페이지 - 퀴즈 제출 후 결과 확인
    path(
        "mission/result/<int:attempt_id>/",
        views.MissionResultView.as_view(),
        name="mission_result",
    ),
    # 프로젝트 제출 페이지 - 중간/기말고사 프로젝트 제출
    path(
        "subject/<int:subject_id>/project/submit/",
        views.SubmitProjectView.as_view(),
        name="submit_project",
    ),
    # 프로젝트 상세 페이지 - 제출된 프로젝트 정보와 피드백 확인
    path(
        "project/<int:submission_id>/",
        views.ProjectDetailView.as_view(),
        name="project_detail",
    ),
    # 수료증 발급 - 과정 완료 후 수료증 발급 요청
    path(
        "enrollment/<int:enrollment_id>/certificate/issue/",
        views.IssueCertificateView.as_view(),
        name="issue_certificate",
    ),
    # 수료증 보기 - 발급된 수료증 웹 페이지로 확인
    path(
        "certificate/<int:certificate_id>/",
        views.ViewCertificateView.as_view(),
        name="view_certificate",
    ),
    # 수료증 다운로드 - PDF 형식으로 수료증 다운로드
    path(
        "certificate/<int:certificate_id>/download/",
        views.DownloadCertificateView.as_view(),
        name="download_certificate",
    ),
]
