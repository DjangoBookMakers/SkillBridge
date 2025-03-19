from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect, get_object_or_404
from django.views.generic import ListView, DetailView
from django.views import View
import logging

from admin_portal.mixins import AdminRequiredMixin
from courses.models import Course, QnAQuestion, QnAAnswer

logger = logging.getLogger("django")


class QnAManagementView(AdminRequiredMixin, ListView):
    """Q&A 관리 페이지"""

    model = QnAQuestion
    template_name = "admin_portal/qna_management.html"
    context_object_name = "questions"
    paginate_by = 20

    def get_queryset(self):
        search_query = self.request.GET.get("search", "")
        course_id = self.request.GET.get("course_id", "")
        status_filter = self.request.GET.get("status", "all")

        # 기본 쿼리셋
        queryset = QnAQuestion.objects.select_related(
            "user", "lecture", "lecture__subject", "lecture__subject__course"
        ).order_by("-created_at")

        # 검색 필터 적용
        if search_query:
            queryset = queryset.filter(
                Q(content__icontains=search_query)
                | Q(user__username__icontains=search_query)
                | Q(lecture__title__icontains=search_query)
            )

        # 과정 필터 적용
        if course_id:
            queryset = queryset.filter(lecture__subject__course_id=course_id)

        # 답변 상태 필터 적용
        if status_filter == "answered":
            queryset = queryset.filter(answers__isnull=False).distinct()
        elif status_filter == "unanswered":
            queryset = queryset.filter(answers__isnull=True)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 필터링 옵션을 컨텍스트에 추가
        context["search_query"] = self.request.GET.get("search", "")
        context["course_id"] = self.request.GET.get("course_id", "")
        context["status_filter"] = self.request.GET.get("status", "all")

        # 과정 목록 추가
        context["courses"] = Course.objects.all().order_by("title")

        return context


class QnADetailView(AdminRequiredMixin, DetailView):
    """Q&A 상세 보기 페이지"""

    model = QnAQuestion
    template_name = "admin_portal/qna_detail.html"
    context_object_name = "question"
    pk_url_kwarg = "question_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        question = self.get_object()

        # 관련 답변들 가져오기
        context["answers"] = question.answers.all().order_by("created_at")

        return context


class AddAnswerView(AdminRequiredMixin, View):
    """질문에 대한 답변 추가"""

    def post(self, request, question_id):
        question = get_object_or_404(QnAQuestion, id=question_id)
        content = request.POST.get("content", "").strip()

        if content:
            # 답변 생성
            QnAAnswer.objects.create(
                user=request.user, question=question, content=content
            )

            logger.info(
                f"Admin {request.user.username} added answer to question {question_id}"
            )
            messages.success(request, "답변이 성공적으로 등록되었습니다.")
        else:
            messages.error(request, "답변 내용을 입력해주세요.")

        return redirect("admin_portal:qna_detail", question_id=question_id)


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

        return redirect("admin_portal:qna_detail", question_id=answer.question.id)


class DeleteAnswerView(AdminRequiredMixin, View):
    """답변 삭제"""

    def post(self, request, answer_id):
        answer = get_object_or_404(QnAAnswer, id=answer_id)
        question_id = answer.question.id

        # 답변 삭제
        answer.delete()

        logger.info(f"Admin {request.user.username} deleted answer {answer_id}")
        messages.success(request, "답변이 성공적으로 삭제되었습니다.")

        return redirect("admin_portal:qna_detail", question_id=question_id)
