from django.db.models import Avg
from django.shortcuts import render
from .models import Course


def course_list(request):
    # 인기 과정 (각 과정의 평균 평점으로 정렬)
    # 평점이 동일하거나 NULL인 경우, 최신 과정이 먼저 표시
    popular_courses = Course.objects.annotate(
        avg_rating=Avg("reviews__rating")
    ).order_by("-avg_rating", "-created_at")[:6]

    # 전체 과정 (최신순)
    all_courses = Course.objects.all().order_by("-created_at")

    context = {
        "popular_courses": popular_courses,
        "all_courses": all_courses,
    }

    return render(request, "courses/course_list.html", context)
