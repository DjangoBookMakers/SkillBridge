from django.urls import path
from . import views

app_name = "courses"

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("detail/<int:course_id>/", views.course_detail, name="course_detail"),
    path("detail/<int:course_id>/review/", views.add_review, name="add_review"),
    path("review/<int:review_id>/update/", views.update_review, name="update_review"),
    path("review/<int:review_id>/delete/", views.delete_review, name="delete_review"),
    path(
        "lecture/<int:lecture_id>/question/add/",
        views.add_question,
        name="add_question",
    ),
    path(
        "question/<int:question_id>/answer/add/",
        views.add_answer,
        name="add_answer",
    ),
]
