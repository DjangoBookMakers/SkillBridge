from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    # 과정 목록 페이지 - 모든 강의 과정과 인기 과정 표시
    path("", views.CourseListView.as_view(), name="course_list"),
    # 과정 상세 페이지 - 특정 과정의 정보, 커리큘럼, 리뷰 표시
    path("detail/<int:course_id>/", views.CourseDetailView.as_view(), name="detail"),
    # 수강평 추가 - 과정에 대한 리뷰와 평점 등록
    path(
        "detail/<int:course_id>/review/",
        views.AddReviewView.as_view(),
        name="add_review",
    ),
    # 수강평 수정 - 기존 작성한 리뷰 내용과 평점 변경
    path(
        "review/<int:review_id>/update/",
        views.UpdateReviewView.as_view(),
        name="update_review",
    ),
    # 수강평 삭제 - 작성한 리뷰 삭제
    path(
        "review/<int:review_id>/delete/",
        views.DeleteReviewView.as_view(),
        name="delete_review",
    ),
    # 강의 질문 등록 - 특정 강의에 대한 질문 작성
    path(
        "lecture/<int:lecture_id>/question/add/",
        views.AddQuestionView.as_view(),
        name="add_question",
    ),
    # 질문 답변 등록 - 관리자가 강의 질문에 대한 답변 작성
    path(
        "question/<int:question_id>/answer/add/",
        views.AddAnswerView.as_view(),
        name="add_answer",
    ),
]
