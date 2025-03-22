from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Avg
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import ListView, DetailView
import json
import logging

from admin_portal.mixins import AdminRequiredMixin
from learning.models import Enrollment, LectureProgress, ProjectSubmission
from payments.models import Cart, CartItem
from .models import Course, Subject, Lecture, QnAQuestion, QnAAnswer, CourseReview

logger = logging.getLogger("django")


class CourseListView(ListView):
    """과정 목록 페이지

    모든 강의 과정과 인기 과정을 표시합니다.
    """

    model = Course
    template_name = "courses/course_list.html"
    context_object_name = "all_courses"
    paginate_by = 12

    def get_queryset(self):
        # 전체 과정 (최신순)
        return Course.objects.all().order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 인기 과정 (각 과정의 평균 평점으로 정렬)
        # 평점이 동일하거나 NULL인 경우, 최신 과정이 먼저 표시
        popular_courses = Course.objects.annotate(
            avg_rating=Avg("reviews__rating")
        ).order_by("-avg_rating", "-created_at")[:6]

        context["popular_courses"] = popular_courses

        # 배너에 표시할 인기 과정 상위 3개
        banner_courses = popular_courses[:3]

        # 배너 슬라이드 데이터 생성
        banner_slides = []
        for course in banner_courses:
            # 제목을 두 줄로 분리 (가정: 첫 번째 공백을 기준으로 나눔)
            title_parts = course.title.split(" ", 1)
            title_line1 = title_parts[0] if len(title_parts) > 0 else course.title
            title_line2 = (
                title_parts[1] if len(title_parts) > 1 else "나노 디그리로 완성하세요"
            )

            slide = {
                "titleLine1": title_line1,
                "titleLine2": title_line2,
                "description": course.short_description
                or "실무에 필요한 기술을 습득하세요.",
                "courseDetailUrl": f"/courses/detail/{course.id}/",
                "course": course,
            }
            banner_slides.append(slide)

        context["banner_slides"] = banner_slides

        return context


class CourseDetailView(DetailView):
    """과정 상세 페이지

    특정 과정의 정보, 커리큘럼, 리뷰를 표시합니다.
    """

    model = Course
    template_name = "courses/course_detail.html"
    context_object_name = "course"
    pk_url_kwarg = "course_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()

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
        enrollment = None

        if self.request.user.is_authenticated:
            enrollment = Enrollment.objects.filter(
                user=self.request.user, course=course
            ).first()
            is_enrolled = enrollment is not None

            logger.info(
                f"User {self.request.user.username} viewing course detail: {course.title} (enrolled: {is_enrolled})"
            )

            # 장바구니에 담겨있는지 확인
            cart = Cart.objects.filter(user=self.request.user).first()
            if cart:
                is_in_cart = CartItem.objects.filter(cart=cart, course=course).exists()

        # 완료된 강의 ID 목록
        completed_lectures = []
        if self.request.user.is_authenticated and is_enrolled:
            completed_lectures = LectureProgress.objects.filter(
                enrollment=enrollment,
                is_completed=True,
            ).values_list("lecture_id", flat=True)

        # 프로젝트 제출/통과 상태 확인
        passed_projects = []
        submitted_projects = []

        if self.request.user.is_authenticated and is_enrolled:
            # 통과한 프로젝트
            passed_projects = ProjectSubmission.objects.filter(
                enrollment=enrollment, is_passed=True
            ).values_list("subject_id", flat=True)

            # 제출했지만 아직 검토 중인 프로젝트
            submitted_projects = ProjectSubmission.objects.filter(
                enrollment=enrollment,
                is_passed=False,
                reviewed_at__isnull=True,
            ).values_list("subject_id", flat=True)

        context.update(
            {
                "subjects": subjects,
                "reviews": reviews,
                "is_enrolled": is_enrolled,
                "is_in_cart": is_in_cart,
                "completed_lectures": completed_lectures,
                "passed_projects": passed_projects,
                "submitted_projects": submitted_projects,
            }
        )

        return context


class AddReviewView(LoginRequiredMixin, View):
    """수강평 추가

    이미 리뷰가 있으면 수정하고, 없으면 새로 생성합니다.
    """

    def post(self, request, course_id):
        course = get_object_or_404(Course, id=course_id)

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


class UpdateReviewView(LoginRequiredMixin, View):
    """수강평 수정

    기존 작성한 리뷰 내용과 평점을 변경합니다.
    사용자 본인의 리뷰만 수정할 수 있습니다.
    """

    def post(self, request, review_id):
        review = get_object_or_404(CourseReview, id=review_id)

        # 권한 체크 (본인의 리뷰만 수정 가능)
        if review.user != request.user:
            logger.warning(
                f"User {request.user.username} attempted to update review {review_id} belonging to {review.user.username}"
            )
            return JsonResponse(
                {"success": False, "message": "수정 권한이 없습니다."}, status=403
            )

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


class DeleteReviewView(LoginRequiredMixin, View):
    """수강평 삭제

    작성한 리뷰를 삭제합니다.
    사용자 본인의 리뷰만 삭제할 수 있습니다.
    """

    def post(self, request, review_id):
        review = get_object_or_404(CourseReview, id=review_id)

        # 권한 체크 (본인의 리뷰만 삭제 가능)
        if review.user != request.user:
            return JsonResponse(
                {"success": False, "message": "삭제 권한이 없습니다."}, status=403
            )

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


class AddQuestionView(LoginRequiredMixin, View):
    """강의에 질문 추가

    특정 강의에 대한 질문을 작성합니다.
    """

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, id=lecture_id)
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


class AddAnswerView(AdminRequiredMixin, View):
    """질문에 답변 추가 (관리자 전용)

    관리자가 강의 질문에 대한 답변을 작성합니다.
    관리자 권한이 필요합니다.
    """

    def post(self, request, question_id):
        question = get_object_or_404(QnAQuestion, id=question_id)
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


class UpdateAnswerView(AdminRequiredMixin, View):
    """답변 수정"""

    def post(self, request, answer_id):
        answer = get_object_or_404(QnAAnswer, id=answer_id)
        content = request.POST.get("content", "").strip()

        # 권한 확인 (원래는 본인이 작성한 답변만 수정할 수 있지만, 관리자는 모든 답변 수정 가능)

        if content:
            # 답변 내용 업데이트
            answer.content = content
            answer.save()

            logger.info(f"Admin {request.user.username} updated answer {answer_id}")
            messages.success(request, "답변이 성공적으로 수정되었습니다.")
        else:
            messages.error(request, "답변 내용을 입력해주세요.")

        # 이전 페이지로 리다이렉트
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)

        return redirect("learning:video_lecture", lecture_id=answer.question.lecture.id)


class DeleteAnswerView(AdminRequiredMixin, View):
    """답변 삭제"""

    def post(self, request, answer_id):
        answer = get_object_or_404(QnAAnswer, id=answer_id)
        lecture_id = answer.question.lecture.id

        # 답변 삭제
        answer.delete()

        logger.info(f"Admin {request.user.username} deleted answer {answer_id}")
        messages.success(request, "답변이 성공적으로 삭제되었습니다.")

        # 이전 페이지로 리다이렉트
        referer = request.META.get("HTTP_REFERER")
        if referer:
            return redirect(referer)

        return redirect("learning:video_lecture", lecture_id=lecture_id)
