from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("course/<int:course_id>/", views.course_detail, name="course_detail"),
    path("course/<int:course_id>/review/", views.add_review, name="course_add_review"),
    path(
        "review/<int:review_id>/update/",
        views.update_review,
        name="course_update_review",
    ),
    path(
        "review/<int:review_id>/delete/",
        views.delete_review,
        name="course_delete_review",
    ),
    path(
        "lecture/<int:lecture_id>/question/add/",
        views.add_question,
        name="course_add_question",
    ),
    path(
        "question/<int:question_id>/answer/add/",
        views.add_answer,
        name="course_add_answer",
    ),
]
