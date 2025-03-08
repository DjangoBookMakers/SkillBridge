from django.urls import path
from . import views

urlpatterns = [
    path("", views.course_list, name="course_list"),
    path("detail/<int:course_id>/", views.course_detail, name="course_detail"),
    path("detail/<int:course_id>/review/", views.add_review, name="course_add_review"),
]
