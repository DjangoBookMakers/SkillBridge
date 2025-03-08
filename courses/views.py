from django.db.models import Avg
from django.shortcuts import get_object_or_404, render
from .models import Course, Subject, Lecture, CourseReview


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


def course_detail(request, course_id):
    # 특정 과정 가져오기
    course = get_object_or_404(Course, id=course_id)

    # 과목 목록 가져오기
    subjects = Subject.objects.filter(course=course).order_by("order_index")

    # 각 과목에 대한 강의 목록 가져오기
    for subject in subjects:
        subject.lecture_list = Lecture.objects.filter(subject=subject).order_by(
            "order_index"
        )

    # 해당 과정에 대한 리뷰 가져오기
    reviews = course.reviews.all().order_by("-created_at")

    # 사용자가 이미 이 과정을 구매했는지 확인
    is_enrolled = False
    # TODO: Enrollment 모델 구현 뒤 사용
    # if request.user.is_authenticated:
    #     # Enrollment 모델에 따라 수정 필요
    #     is_enrolled = hasattr(request.user, 'enrollments') and request.user.enrollments.filter(course=course).exists()

    context = {
        "course": course,
        "subjects": subjects,
        "reviews": reviews,
        "is_enrolled": is_enrolled,
    }

    return render(request, "courses/course_detail.html", context)


from django.shortcuts import redirect
from django.contrib.auth.decorators import login_required


@login_required
def add_review(request, course_id):
    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        rating = request.POST.get("rating")
        content = request.POST.get("content")

        # 이미 리뷰가 있는지 확인
        existing_review = course.reviews.filter(user=request.user).first()

        if existing_review:
            # 기존 리뷰 업데이트
            existing_review.rating = rating
            existing_review.content = content
            existing_review.save()
        else:
            # 새 리뷰 생성
            CourseReview.objects.create(
                user=request.user, course=course, rating=rating, content=content
            )

    return redirect("courses:course_detail", course_id=course_id)
