from django.shortcuts import render
from .models import Course


def course_list(request):
    # 인기 과정 (리뷰 평점 기준으로 상위 6개)
    # popular_courses = Course.objects.all().order_by('-reviews__rating')[:6]

    # 중복 제거를 위한 처리 (같은 과정이 여러 리뷰를 받은 경우)
    # popular_courses = list(dict.fromkeys(popular_courses))

    # 전체 과정 (최신순)
    all_courses = Course.objects.all().order_by("-created_at")

    context = {
        # 'popular_courses': popular_courses,
        "popular_courses": [],
        "all_courses": all_courses,
    }

    return render(request, "courses/course_list.html", context)
