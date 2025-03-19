from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import TemplateView, FormView, DetailView
import logging

from courses.models import Course, Subject, Lecture, MissionQuestion, QnAQuestion
from .forms import ProjectSubmissionForm
from .models import (
    Enrollment,
    LectureProgress,
    MissionAttempt,
    ProjectSubmission,
    Certificate,
)

logger = logging.getLogger("django")


class DashboardView(LoginRequiredMixin, TemplateView):
    """학습 대시보드"""

    template_name = "learning/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 사용자의 수강 중인 과정 목록
        enrollments = Enrollment.objects.filter(user=self.request.user).order_by(
            "-enrolled_at"
        )

        # 진행 중인 과정과 완료된 과정 분리
        in_progress = [e for e in enrollments if e.status == "enrolled"]
        completed = [e for e in enrollments if e.status in ["completed", "certified"]]

        # 수료증 목록
        certificates = Certificate.objects.filter(user=self.request.user).order_by(
            "-issued_at"
        )

        context.update(
            {
                "in_progress": in_progress,
                "completed": completed,
                "certificates": certificates,
            }
        )
        return context


class ResumeCourseView(LoginRequiredMixin, View):
    """이어서 학습하기"""

    def get(self, request, course_id):
        # 과정 정보 가져오기
        course = get_object_or_404(Course, id=course_id)

        # 수강 신청 여부 확인
        enrollment = get_object_or_404(Enrollment, user=request.user, course=course)

        # 다음 학습 항목 가져오기
        item_type, item = enrollment.get_next_learning_item()

        logger.info(
            f"User {request.user.username} resuming course {course.title}: next item type={item_type}"
        )

        # 항목 유형에 따라 적절한 URL로 리다이렉트
        if item_type == "video_lecture":
            return redirect("learning:video_lecture", lecture_id=item.id)
        elif item_type == "mission":
            return redirect("learning:mission", lecture_id=item.id)
        elif item_type == "project":
            return redirect("learning:submit_project", subject_id=item.id)
        else:  # 'completed'
            return redirect("courses:detail", course_id=course.id)


class NextItemView(LoginRequiredMixin, View):
    """현재 강의 다음의 학습 항목으로 이동"""

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, id=lecture_id)

        # 다음 학습 항목 가져오기
        item_type, item = lecture.get_next_learning_item()

        # 항목 유형에 따라 적절한 URL로 리다이렉트
        if item_type == "video_lecture":
            return redirect("learning:video_lecture", lecture_id=item.id)
        elif item_type == "mission":
            return redirect("learning:mission", lecture_id=item.id)
        elif item_type == "project":
            return redirect("learning:submit_project", subject_id=item.id)
        else:  # 'completed'
            return redirect("courses:detail", course_id=item.id)


class VideoLectureView(LoginRequiredMixin, DetailView):
    """동영상 강의 시청"""

    model = Lecture
    template_name = "learning/video_lecture.html"
    context_object_name = "lecture"
    pk_url_kwarg = "lecture_id"

    def get_object(self, queryset=None):
        lecture_id = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(Lecture, id=lecture_id, lecture_type="video")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lecture = self.get_object()

        # 수강 신청 여부 확인
        enrollment = get_object_or_404(
            Enrollment, user=self.request.user, course=lecture.subject.course
        )

        # 강의 시청 기록 생성 또는 업데이트
        lecture_progress, created = LectureProgress.objects.get_or_create(
            user=self.request.user, lecture=lecture
        )

        # 시청 완료 처리 (강의에 접근하는 것만으로도 완료 처리)
        if not lecture_progress.is_completed:
            logger.info(
                f"User {self.request.user.username} completed lecture: {lecture.title} (id: {lecture.id})"
            )
            lecture_progress.mark_as_completed()

        # 이전/다음 강의 찾기
        subject_lectures = Lecture.objects.filter(subject=lecture.subject).order_by(
            "order_index"
        )

        current_index = next(
            (i for i, l in enumerate(subject_lectures) if l.id == lecture.id), None
        )

        prev_lecture = (
            subject_lectures[current_index - 1] if current_index > 0 else None
        )
        next_lecture = (
            subject_lectures[current_index + 1]
            if current_index < len(subject_lectures) - 1
            else None
        )

        # 해당 강의에 대한 질문 목록
        questions = QnAQuestion.objects.filter(lecture=lecture).order_by("-created_at")

        context.update(
            {
                "subject": lecture.subject,
                "course": lecture.subject.course,
                "prev_lecture": prev_lecture,
                "next_lecture": next_lecture,
                "questions": questions,
                "enrollment": enrollment,
            }
        )
        return context


class MissionView(LoginRequiredMixin, View):
    """미션(쪽지시험) 수행"""

    template_name = "learning/mission.html"

    def get(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, id=lecture_id, lecture_type="mission")

        # 수강 신청 여부 확인
        enrollment = get_object_or_404(
            Enrollment, user=request.user, course=lecture.subject.course
        )

        # 이미 통과한 미션인지 확인
        passed_attempt = MissionAttempt.objects.filter(
            user=request.user, lecture=lecture, is_passed=True
        ).first()

        if passed_attempt:
            logger.info(
                f"User {request.user.username} accessing already passed mission: {lecture.title}"
            )
            return redirect("learning:mission_result", attempt_id=passed_attempt.id)

        # 문제 목록 가져오기
        questions = MissionQuestion.objects.filter(lecture=lecture).order_by(
            "order_index"
        )

        context = {
            "lecture": lecture,
            "subject": lecture.subject,
            "course": lecture.subject.course,
            "questions": questions,
            "enrollment": enrollment,
        }
        return render(request, self.template_name, context)

    def post(self, request, lecture_id):
        lecture = get_object_or_404(Lecture, id=lecture_id, lecture_type="mission")

        logger.info(
            f"User {request.user.username} submitted answers for mission: {lecture.title}"
        )

        # POST 요청에서 사용자 답안 수집
        user_answers = {}
        for key, value in request.POST.items():
            if key.startswith("question_"):
                question_id = key.replace("question_", "")
                user_answers[question_id] = value

        # 시도 중인 미션이 있는지 확인
        active_attempt = MissionAttempt.objects.filter(
            user=request.user, lecture=lecture, completed_at__isnull=True
        ).first()

        # 기존 미션 시도가 있으면 업데이트, 없으면 새로 생성
        if active_attempt:
            attempt = active_attempt
            attempt.user_answers = user_answers
        else:
            attempt = MissionAttempt(
                user=request.user, lecture=lecture, user_answers=user_answers
            )

        # 저장 및 점수 계산
        attempt.save()
        attempt.calculate_score()

        # 결과 페이지로 리다이렉트
        return redirect("learning:mission_result", attempt_id=attempt.id)


class MissionResultView(LoginRequiredMixin, DetailView):
    """미션 결과 확인"""

    model = MissionAttempt
    template_name = "learning/mission_result.html"
    context_object_name = "attempt"
    pk_url_kwarg = "attempt_id"

    def get_object(self, queryset=None):
        attempt_id = self.kwargs.get(self.pk_url_kwarg)
        return get_object_or_404(MissionAttempt, id=attempt_id, user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        attempt = self.get_object()
        lecture = attempt.lecture

        # 문제 정보 가져오기
        questions = MissionQuestion.objects.filter(lecture=lecture).order_by(
            "order_index"
        )

        # 문제별 사용자 답안 및 정답 매칭
        results = []
        for question in questions:
            user_answer = attempt.user_answers.get(str(question.id), None)
            is_correct = user_answer and int(user_answer) == question.correct_answer

            results.append(
                {
                    "question": question,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                }
            )

        context.update(
            {
                "lecture": lecture,
                "subject": lecture.subject,
                "course": lecture.subject.course,
                "results": results,
                "total_questions": len(questions),
                "correct_count": sum(1 for r in results if r["is_correct"]),
            }
        )
        return context


class SubmitProjectView(LoginRequiredMixin, FormView):
    """프로젝트 제출 (중간/기말고사)"""

    template_name = "learning/submit_project.html"
    form_class = ProjectSubmissionForm

    def dispatch(self, request, *args, **kwargs):
        self.subject = get_object_or_404(Subject, id=self.kwargs.get("subject_id"))

        # 수강 신청 여부 확인
        self.enrollment = get_object_or_404(
            Enrollment, user=request.user, course=self.subject.course
        )

        # 중간/기말고사 과목인지 확인
        if self.subject.subject_type not in ["midterm", "final"]:
            messages.error(request, "유효하지 않은 접근입니다.")
            return redirect("courses:detail", course_id=self.subject.course.id)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 이미 제출한 프로젝트가 있는지 확인
        existing_submission = (
            ProjectSubmission.objects.filter(
                user=self.request.user, subject=self.subject
            )
            .order_by("-submitted_at")
            .first()
        )

        context.update(
            {
                "subject": self.subject,
                "course": self.subject.course,
                "existing_submission": existing_submission,
                "enrollment": self.enrollment,
            }
        )
        return context

    def form_valid(self, form):
        submission = form.save(commit=False)
        submission.user = self.request.user
        submission.subject = self.subject
        submission.save()

        messages.success(self.request, "프로젝트가 성공적으로 제출되었습니다.")
        return redirect("learning:project_detail", submission_id=submission.id)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """프로젝트 상세 보기"""

    model = ProjectSubmission
    template_name = "learning/project_detail.html"
    context_object_name = "submission"
    pk_url_kwarg = "submission_id"

    def get_object(self, queryset=None):
        submission_id = self.kwargs.get(self.pk_url_kwarg)
        submission = get_object_or_404(ProjectSubmission, id=submission_id)

        # 권한 확인 (제출자 본인 또는 관리자)
        if submission.user != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied

        return submission

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        submission = self.get_object()

        context.update(
            {
                "subject": submission.subject,
                "course": submission.subject.course,
            }
        )
        return context


class IssueCertificateView(LoginRequiredMixin, View):
    """수료증 발급"""

    def get(self, request, enrollment_id):
        enrollment = get_object_or_404(Enrollment, id=enrollment_id, user=request.user)

        # 이미 발급된 수료증이 있는지 확인
        existing_cert = Certificate.objects.filter(enrollment=enrollment).first()
        if existing_cert:
            logger.info(f"Certificate already issued for enrollment {enrollment_id}")
            messages.info(request, "이미 발급된 수료증이 있습니다.")
            return redirect(
                "learning:view_certificate", certificate_id=existing_cert.id
            )

        # 수료 조건 확인
        if enrollment.status != "completed":
            if not enrollment.check_completion():
                logger.warning(
                    f"Certificate issuance failed: User {request.user.username} has not completed course {enrollment.course.title}"
                )
                messages.error(
                    request, "모든 과정을 완료해야 수료증을 발급받을 수 있습니다."
                )
                return redirect("learning:dashboard")

        # 수료증 발급
        certificate = Certificate(user=request.user, enrollment=enrollment)

        # 고유 번호 생성
        certificate.generate_certificate_number()
        logger.info(
            f"Certificate created with number {certificate.certificate_number} for user {request.user.username}"
        )

        # PDF 생성 (실제 구현 필요)
        # certificate.generate_pdf()

        certificate.save()

        # 수강 상태 업데이트
        enrollment.status = "certified"
        enrollment.certificate_number = certificate.certificate_number
        enrollment.certificate_issued_at = certificate.issued_at
        enrollment.save(
            update_fields=["status", "certificate_number", "certificate_issued_at"]
        )

        messages.success(request, "수료증이 성공적으로 발급되었습니다.")
        return redirect("learning:view_certificate", certificate_id=certificate.id)


class ViewCertificateView(LoginRequiredMixin, DetailView):
    """수료증 보기"""

    model = Certificate
    template_name = "learning/view_certificate.html"
    context_object_name = "certificate"
    pk_url_kwarg = "certificate_id"

    def get_object(self, queryset=None):
        certificate_id = self.kwargs.get(self.pk_url_kwarg)
        certificate = get_object_or_404(Certificate, id=certificate_id)

        # 권한 확인 (본인의 수료증만 조회 가능)
        if certificate.user != self.request.user and not self.request.user.is_admin:
            raise PermissionDenied

        return certificate

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.get_object()

        context.update(
            {
                "course": certificate.enrollment.course,
            }
        )
        return context


class DownloadCertificateView(LoginRequiredMixin, View):
    """수료증 PDF 다운로드"""

    def get(self, request, certificate_id):
        certificate = get_object_or_404(Certificate, id=certificate_id)

        # 권한 확인 (본인의 수료증만 다운로드 가능)
        if certificate.user != request.user and not request.user.is_admin:
            logger.warning(
                f"Unauthorized certificate download attempt: user={request.user.username}, certificate={certificate_id}"
            )
            raise PermissionDenied

        # 수료증 PDF 파일이 없으면 생성
        if not certificate.pdf_file:
            logger.info(f"Generating PDF for certificate {certificate_id}")
            certificate.generate_pdf()
            certificate.save()

        # PDF 파일 제공
        try:
            logger.info(
                f"User {request.user.username} downloading certificate {certificate_id}"
            )
            return FileResponse(
                open(certificate.pdf_file.path, "rb"),
                content_type="application/pdf",
                as_attachment=True,
                filename=f"수료증_{certificate.certificate_number}.pdf",
            )
        except Exception as e:
            logger.error(f"Certificate download failed: {str(e)}")
            messages.error(request, f"파일 다운로드 중 오류가 발생했습니다: {str(e)}")
            return redirect("learning:view_certificate", certificate_id=certificate.id)
