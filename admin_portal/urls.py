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
    # 과정 관리
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:course_id>/', views.course_detail, name='course_detail'),
    path('courses/<int:course_id>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:course_id>/delete/', views.course_delete, name='course_delete'),
    
    # 과목 관리
    path('courses/<int:course_id>/subjects/', views.subject_list, name='subject_list'),
    path('courses/<int:course_id>/subjects/create/', views.subject_create, name='subject_create'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/', views.subject_detail, name='subject_detail'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/edit/', views.subject_edit, name='subject_edit'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/delete/', views.subject_delete, name='subject_delete'),
    
    # 강의 관리
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/', views.lecture_list, name='lecture_list'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/create/', views.lecture_create, name='lecture_create'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/', views.lecture_detail, name='lecture_detail'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/edit/', views.lecture_edit, name='lecture_edit'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/delete/', views.lecture_delete, name='lecture_delete'),
    
    # 미션 문제 관리
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/questions/', views.question_list, name='question_list'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/questions/create/', views.question_create, name='question_create'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/questions/<int:question_id>/edit/', views.question_edit, name='question_edit'),
    path('courses/<int:course_id>/subjects/<int:subject_id>/lectures/<int:lecture_id>/questions/<int:question_id>/delete/', views.question_delete, name='question_delete'),
]
