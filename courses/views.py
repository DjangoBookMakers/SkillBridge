from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from django.db.models import Avg
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
import json
import logging

from learning.models import LectureProgress, ProjectSubmission
from payments.models import Cart, CartItem
from .models import Course, Subject, Lecture, QnAQuestion, QnAAnswer, CourseReview

logger = logging.getLogger("django")


def course_list(request):
    # 인기 과정 (각 과정의 평균 평점으로 정렬)
    # 평점이 동일하거나 NULL인 경우, 최신 과정이 먼저 표시
    popular_courses = Course.objects.annotate(
        avg_rating=Avg("reviews__rating")
    ).order_by("-avg_rating", "-created_at")[:6]

    # 전체 과정 (최신순)
    all_courses_list = Course.objects.all().order_by("-created_at")

    # 페이지네이션 (한 페이지에 12개씩 표시)
    paginator = Paginator(all_courses_list, 12)
    page = request.GET.get("page")

    try:
        all_courses = paginator.page(page)
    except PageNotAnInteger:
        # 페이지 번호가, 숫자가 아닐 경우 첫 페이지
        all_courses = paginator.page(1)
    except EmptyPage:
        # 페이지가 범위를 벗어나면 마지막 페이지
        all_courses = paginator.page(paginator.num_pages)

    context = {
        "popular_courses": popular_courses,
        "all_courses": all_courses,
    }

    return render(request, "courses/course_list.html", context)


def detail(request, course_id):
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
    is_in_cart = False

    if request.user.is_authenticated:
        is_enrolled = (
            hasattr(request.user, "enrollments")
            and request.user.enrollments.filter(course=course).exists()
        )

        logger.info(
            f"User {request.user.username} viewing course detail: {course.title} (enrolled: {is_enrolled})"
        )

        # 장바구니에 담겨있는지 확인
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            is_in_cart = CartItem.objects.filter(cart=cart, course=course).exists()

    # 완료된 강의 ID 목록
    completed_lectures = []
    if request.user.is_authenticated and is_enrolled:
        completed_lectures = LectureProgress.objects.filter(
            user=request.user, lecture__subject__course=course, is_completed=True
        ).values_list("lecture_id", flat=True)

    # 프로젝트 제출/통과 상태 확인
    passed_projects = []
    submitted_projects = []

    if request.user.is_authenticated and is_enrolled:
        # 통과한 프로젝트
        passed_projects = ProjectSubmission.objects.filter(
            user=request.user, subject__course=course, is_passed=True
        ).values_list("subject_id", flat=True)

        # 제출했지만 아직 검토 중인 프로젝트
        submitted_projects = ProjectSubmission.objects.filter(
            user=request.user,
            subject__course=course,
            is_passed=False,
            reviewed_at__isnull=True,
        ).values_list("subject_id", flat=True)

    context = {
        "course": course,
        "subjects": subjects,
        "reviews": reviews,
        "is_enrolled": is_enrolled,
        "is_in_cart": is_in_cart,
        "completed_lectures": completed_lectures,
        "passed_projects": passed_projects,
        "submitted_projects": submitted_projects,
    }

    return render(request, "courses/course_detail.html", context)


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
    return redirect("learning:video_lecture", lecture_id=lecture.id)


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
    return redirect("learning:video_lecture", lecture_id=question.lecture.id)


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
            logger.info(
                f"Review updated: user={request.user.username}, course={course.title}, rating={rating}"
            )
        else:
            # 새 리뷰 생성
            review = CourseReview.objects.create(
                user=request.user, course=course, rating=rating, content=content
            )
            logger.info(
                f"New review created: user={request.user.username}, course={course.title}, rating={rating}, id={review.id}"
            )

    return redirect("courses:detail", course_id=course_id)


@login_required
def update_review(request, review_id):
    """수강평 수정"""
    review = get_object_or_404(CourseReview, id=review_id)

    # 권한 체크 (본인의 리뷰만 수정 가능)
    if review.user != request.user:
        logger.warning(
            f"User {request.user.username} attempted to update review {review_id} belonging to {review.user.username}"
        )
        return JsonResponse(
            {"success": False, "message": "수정 권한이 없습니다."}, status=403
        )

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            rating = data.get("rating")
            content = data.get("content")

            if not rating or not content:
                return JsonResponse(
                    {"success": False, "message": "평점과 내용을 모두 입력해주세요."},
                    status=400,
                )

            review.rating = rating
            review.content = content
            review.save()

            logger.info(
                f"Review {review_id} updated: user={request.user.username}, course={review.course.title}, rating={review.rating}"
            )

            return JsonResponse(
                {
                    "success": True,
                    "message": "수강평이 수정되었습니다.",
                    "review": {
                        "id": review.id,
                        "rating": review.rating,
                        "content": review.content,
                        "created_at": review.created_at.strftime("%Y년 %m월 %d일"),
                        "username": review.user.username,
                    },
                }
            )
        except Exception as e:
            logger.error(f"Review update error: {str(e)}")
            return JsonResponse(
                {"success": False, "message": f"오류가 발생했습니다: {str(e)}"},
                status=500,
            )

    return JsonResponse({"success": False, "message": "잘못된 요청입니다."}, status=400)


@login_required
def delete_review(request, review_id):
    """수강평 삭제"""
    review = get_object_or_404(CourseReview, id=review_id)

    # 권한 체크 (본인의 리뷰만 삭제 가능)
    if review.user != request.user:
        return JsonResponse(
            {"success": False, "message": "삭제 권한이 없습니다."}, status=403
        )

    if request.method == "POST":
        try:
            course_id = review.course.id  # 삭제 전에 course_id 저장
            review.delete()
            return JsonResponse(
                {
                    "success": True,
                    "message": "수강평이 삭제되었습니다.",
                    "course_id": course_id,
                }
            )
        except Exception as e:
            return JsonResponse(
                {"success": False, "message": f"오류가 발생했습니다: {str(e)}"},
                status=500,
            )

    return JsonResponse({"success": False, "message": "잘못된 요청입니다."}, status=400)
