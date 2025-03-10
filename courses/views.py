from django.contrib import messages
from django.db.models import Avg
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render

from .models import Course, Subject, Lecture, QnAQuestion, QnAAnswer, CourseReview


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
def add_question(request, lecture_id):
    """강의에 질문 추가"""
    lecture = get_object_or_404(Lecture, id=lecture_id)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if content:
            # 질문 생성
            QnAQuestion.objects.create(
                user=request.user, lecture=lecture, content=content
            )
            messages.success(request, "질문이 등록되었습니다.")
        else:
            messages.error(request, "질문 내용을 입력해주세요.")

    # 요청이 온 페이지로 리다이렉트
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)

    # 기본적으로 강의 비디오 페이지로 리다이렉트
    return redirect("learning_video_lecture", lecture_id=lecture.id)


@login_required
def add_answer(request, question_id):
    """질문에 답변 추가 (관리자 전용)"""
    question = get_object_or_404(QnAQuestion, id=question_id)

    # 관리자만 답변 작성 가능
    if not request.user.is_admin:
        return HttpResponseForbidden("답변을 작성할 권한이 없습니다.")

    if request.method == "POST":
        content = request.POST.get("content", "").strip()

        if content:
            # 답변 생성
            QnAAnswer.objects.create(
                user=request.user, question=question, content=content
            )
            messages.success(request, "답변이 등록되었습니다.")
        else:
            messages.error(request, "답변 내용을 입력해주세요.")

    # 요청이 온 페이지로 리다이렉트
    referer = request.META.get("HTTP_REFERER")
    if referer:
        return redirect(referer)

    # 기본적으로 강의 비디오 페이지로 리다이렉트
    return redirect("learning_video_lecture", lecture_id=question.lecture.id)


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

    return redirect("course_detail", course_id=course_id)
