from django.shortcuts import get_object_or_404, redirect
from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Avg, Q, Min, Sum
from django.db.models.functions import TruncWeek
from django.views import View
from django.views.generic import (
    TemplateView,
    ListView,
    DetailView,
    UpdateView,
    CreateView,
    DeleteView,
)
from datetime import timedelta, date, datetime
import json
import io
import logging
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from accounts.models import DeletedUserData, User, InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion
from learning.models import Enrollment, Certificate, LectureProgress, ProjectSubmission
from payments.models import Payment
from payments.payment_client import payment_client
from .models import DailyStatistics
from .mixins import AdminRequiredMixin

logger = logging.getLogger("django")


class AdminDashboardView(AdminRequiredMixin, TemplateView):
    """관리자 대시보드 메인 뷰

    플랫폼의 주요 통계 데이터를 시각화하고 보여주는 대시보드 페이지입니다.
    사용자 수, 과정 수, 수강신청 수, 수료증 발급 수 등의 통계와
    차트 데이터를 포함합니다.
    """

    template_name = "admin_portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 오늘 날짜
        today = timezone.now().date()

        # 통계 업데이트
        stats = DailyStatistics.update_daily_statistics()
        logger.info(
            f"Daily statistics updated for {today}: new_users={stats.new_users}, active_users={stats.active_users}"
        )

        # 전체 통계 데이터
        context["total_students"] = User.objects.filter(is_admin=False).count()
        context["total_courses"] = Course.objects.count()
        context["total_enrollments"] = Enrollment.objects.count()
        context["total_certificates"] = Certificate.objects.count()
        context["total_video_views"] = LectureProgress.objects.filter(
            is_completed=True
        ).count()
        context["total_sales"] = (
            Payment.objects.filter(payment_status="completed").aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )
        context["today_sales"] = (
            Payment.objects.filter(
                payment_status="completed", created_at__date=today
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # 최근 30일간 통계
        last_30_days = today - timedelta(days=30)
        daily_stats = DailyStatistics.objects.filter(date__gte=last_30_days).order_by(
            "date"
        )

        # 과정별 수강생 수
        context["course_enrollments"] = (
            Course.objects.annotate(student_count=Count("enrollments"))
            .values("title", "student_count")
            .order_by("-student_count")[:10]
        )

        # 평가 대기 중인 프로젝트
        context["pending_projects"] = (
            ProjectSubmission.objects.filter(is_passed=False, reviewed_at__isnull=True)
            .select_related("user", "subject")
            .order_by("-submitted_at")[:10]
        )

        # 그래프 데이터 준비
        dates = [stat.date.strftime("%Y-%m-%d") for stat in daily_stats]
        new_users_data = [stat.new_users for stat in daily_stats]
        active_users_data = [stat.active_users for stat in daily_stats]
        new_enrollments_data = [stat.new_enrollments for stat in daily_stats]
        video_views_data = [stat.completed_lectures for stat in daily_stats]
        revenue_data = [float(stat.revenue) for stat in daily_stats]

        # 차트 데이터 JSON 형식으로 변환
        chart_data = {
            "dates": dates,
            "new_users": new_users_data,
            "active_users": active_users_data,
            "new_enrollments": new_enrollments_data,
            "completed_lectures": video_views_data,
            "revenue": revenue_data,
        }

        context["chart_data"] = json.dumps(chart_data)
        context["today_stats"] = DailyStatistics.objects.filter(date=today).first()

        return context


class AdminStatisticsAPIView(AdminRequiredMixin, View):
    """대시보드 통계 데이터 API (AJAX 요청용)

    대시보드의 차트에 표시할 통계 데이터를 JSON 형식으로 반환합니다.
    기간(7일, 30일, 90일)을 받아서 해당 기간의 통계 데이터를 제공합니다.
    """

    def get(self, request, *args, **kwargs):
        period = request.GET.get("period", "30")  # 기본값은 30일

        try:
            days = int(period)
            if days <= 0:
                raise ValueError
        except ValueError:
            return JsonResponse({"error": "유효하지 않은 기간입니다."}, status=400)

        # 기간에 따른 통계 데이터 조회
        today = timezone.now().date()
        start_date = today - timedelta(days=days)
        stats = DailyStatistics.objects.filter(date__gte=start_date).order_by("date")

        # 데이터 포맷팅
        data = {
            "dates": [stat.date.strftime("%Y-%m-%d") for stat in stats],
            "new_users": [stat.new_users for stat in stats],
            "active_users": [stat.active_users for stat in stats],
            "new_enrollments": [stat.new_enrollments for stat in stats],
            "completed_lectures": [stat.completed_lectures for stat in stats],
            "certificates_issued": [stat.certificates_issued for stat in stats],
            "revenue": [float(stat.revenue) for stat in stats],
        }

        return JsonResponse(data)


class PendingProjectsListView(AdminRequiredMixin, ListView):
    """평가 대기 중인 프로젝트 목록 페이지

    학생들이 제출한 프로젝트 목록을 보여주고, 평가 상태별로 필터링할 수 있습니다.
    검색 기능을 통해 특정 학생이나 과목의 프로젝트를 찾을 수 있습니다.
    """

    model = ProjectSubmission
    template_name = "admin_portal/pending_projects.html"
    context_object_name = "projects"
    paginate_by = 10

    def get_queryset(self):
        # 검색 및 필터링
        search_query = self.request.GET.get("search", "")
        status_filter = self.request.GET.get("status", "pending")

        # 기본 쿼리셋 생성
        queryset = ProjectSubmission.objects.select_related(
            "user", "subject", "subject__course"
        )

        # 상태 필터 적용
        if status_filter == "all":
            pass  # 모든 프로젝트 표시
        elif status_filter == "pending":
            queryset = queryset.filter(is_passed=False, reviewed_at__isnull=True)
        elif status_filter == "reviewed":
            queryset = queryset.filter(reviewed_at__isnull=False)
        elif status_filter == "passed":
            queryset = queryset.filter(is_passed=True)

        # 검색 필터 적용
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query)
                | Q(subject__title__icontains=search_query)
                | Q(subject__course__title__icontains=search_query)
            )

        # 정렬
        return queryset.order_by("-submitted_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("search", "")
        context["status_filter"] = self.request.GET.get("status", "pending")
        return context


class ProjectDetailView(AdminRequiredMixin, DetailView):
    """프로젝트 제출 상세 보기

    학생이 제출한 프로젝트의 상세 정보를 보여줍니다.
    프로젝트 파일, 제출자 정보, 평가 상태, 피드백 등을 포함합니다.
    """

    model = ProjectSubmission
    template_name = "admin_portal/project_detail.html"
    context_object_name = "project"
    pk_url_kwarg = "project_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subject"] = self.object.subject
        context["course"] = self.object.subject.course
        return context


class EvaluateProjectView(AdminRequiredMixin, DetailView):
    """프로젝트 평가 페이지

    관리자가 학생이 제출한 프로젝트를 평가하는 페이지입니다.
    통과 여부를 선택하고 피드백을 작성할 수 있습니다.
    평가 결과는 학생의 과정 진행 상황에 반영됩니다.
    """

    model = ProjectSubmission
    template_name = "admin_portal/evaluate_project.html"
    context_object_name = "project"
    pk_url_kwarg = "project_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["subject"] = self.object.subject
        context["course"] = self.object.subject.course
        return context

    def post(self, request, *args, **kwargs):
        project: ProjectSubmission = self.get_object()

        # 평가 처리
        is_passed = request.POST.get("is_passed") == "true"
        feedback = request.POST.get("feedback", "")

        project.is_passed = is_passed
        project.feedback = feedback
        project.reviewed_at = timezone.now()
        project.reviewed_by = request.user
        project.save()

        logger.info(
            f"Project {project.id} evaluated by {request.user.username}, result: {'pass' if is_passed else 'fail'}"
        )
        messages.success(request, "프로젝트 평가가 완료되었습니다.")

        # 학생이 이 프로젝트를 통과했다면 해당 과목의 진행 상태 업데이트
        if is_passed:
            try:
                enrollment = Enrollment.objects.get(
                    user=project.user, course=project.subject.course
                )
                enrollment.check_completion()

                if enrollment.status == "completed":
                    logger.info(
                        f"User {project.user.username} completed course {project.subject.course.title}"
                    )
                    messages.info(
                        request,
                        f"{project.user.username}님의 과정 완료 처리가 되었습니다.",
                    )
            except Enrollment.DoesNotExist:
                logger.error(
                    f"Enrollment not found for user {project.user.username} and course {project.subject.course.id}"
                )

        return redirect("admin_portal:project_detail", project_id=project.id)


class CourseProgressOverviewView(AdminRequiredMixin, TemplateView):
    """과정 진행 상황 개요 페이지

    모든 과정의 진행 상황을 한눈에 볼 수 있는 개요 페이지입니다.
    과정별 평균 진행률, 수강생 수, 수료증 발급 현황 등의 정보를 제공합니다.
    주간 수료증 발급 횟수 차트와 수강생별 평균 진행률 정보도 포함합니다.
    """

    template_name = "admin_portal/course_progress/overview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 모든 과정 목록
        courses = Course.objects.all().order_by("title")

        # 각 과정별 평균 진행률 계산
        courses_progress = []
        for course in courses:
            enrollments = Enrollment.objects.filter(course=course)
            enrollment_count = enrollments.count()

            if enrollment_count > 0:
                avg_progress = enrollments.aggregate(Avg("progress_percentage"))[
                    "progress_percentage__avg"
                ]

                # 수료증 발급 수
                certificate_count = Certificate.objects.filter(
                    enrollment__course=course
                ).count()

                # 최근 일주일간 수료증 발급 수
                week_ago = timezone.now() - timedelta(days=7)
                weekly_certificates = Certificate.objects.filter(
                    enrollment__course=course, issued_at__gte=week_ago
                ).count()

                # 수강생 수
                student_count = enrollment_count

                courses_progress.append(
                    {
                        "course": course,
                        "avg_progress": round(avg_progress if avg_progress else 0, 1),
                        "student_count": student_count,
                        "certificate_count": certificate_count,
                        "weekly_certificates": weekly_certificates,
                    }
                )

        # 주간 수료증 발급 횟수 데이터 (최근 12주)
        twelve_weeks_ago = timezone.now() - timedelta(weeks=12)
        weekly_certificates = (
            Certificate.objects.filter(issued_at__gte=twelve_weeks_ago)
            .annotate(week=TruncWeek("issued_at"))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )

        # 데이터가 없을 경우를 대비해 빈 주간 데이터 생성
        all_weeks = []
        current = twelve_weeks_ago
        today = timezone.now()

        while current <= today:
            week_start = current - timedelta(days=current.weekday())
            all_weeks.append(week_start.date())
            current += timedelta(weeks=1)

        # 실제 데이터가 있는 주만 추출
        existing_weeks = {cert["week"].date() for cert in weekly_certificates}

        # 모든 주에 대한 데이터 구성
        weeks_data = []
        counts_data = []

        for week in all_weeks:
            weeks_data.append(week)
            if week in existing_weeks:
                for cert in weekly_certificates:
                    if cert["week"].date() == week:
                        counts_data.append(cert["count"])
                        break
            else:
                counts_data.append(0)

        weekly_data = {
            "weeks": [week.strftime("%Y-%m-%d") for week in weeks_data],
            "counts": counts_data,
        }

        # 전체 수강생별 평균 진행률 (상위 10명)
        student_progress = []
        students = User.objects.filter(is_admin=False)
        for student in students:
            enrollments = Enrollment.objects.filter(user=student)
            if enrollments.exists():
                avg_progress = enrollments.aggregate(Avg("progress_percentage"))[
                    "progress_percentage__avg"
                ]
                completed_count = enrollments.filter(
                    status__in=["completed", "certified"]
                ).count()
                total_count = enrollments.count()

                student_progress.append(
                    {
                        "student": student,
                        "avg_progress": round(avg_progress if avg_progress else 0, 1),
                        "completed_count": completed_count,
                        "total_count": total_count,
                    }
                )

        # 평균 진행률 기준으로 내림차순 정렬 후 상위 10명만 선택
        student_progress.sort(key=lambda x: x["avg_progress"], reverse=True)
        top_students = student_progress[:10]

        context.update(
            {
                "courses_progress": courses_progress,
                "weekly_certificate_data": json.dumps(weekly_data),
                "top_students": top_students,
            }
        )

        return context


class CourseProgressDetailView(AdminRequiredMixin, DetailView):
    """특정 과정의 상세 진행 상황 페이지

    특정 과정에 대한 상세 진행 상황을 보여주는 페이지입니다.
    과정의 구성(과목, 강의)과 각 수강생별 진행 상황을 표시합니다.
    수강생의 과목별 완료 상태, 진행률, 수료증 발급 여부 등을 확인할 수 있습니다.
    """

    model = Course
    template_name = "admin_portal/course_progress/detail.html"
    context_object_name = "course"
    pk_url_kwarg = "course_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()

        # 과정에 등록된 모든 수강생
        enrollments = Enrollment.objects.filter(course=course).select_related("user")

        # 과목 및 강의 정보
        subjects = Subject.objects.filter(course=course).order_by("order_index")
        subject_data = []

        for subject in subjects:
            lectures = Lecture.objects.filter(subject=subject).order_by("order_index")
            subject_data.append(
                {
                    "subject": subject,
                    "lectures": lectures,
                    "lecture_count": lectures.count(),
                }
            )

        # 수강생별 진행 상황
        student_progress = []
        for enrollment in enrollments:
            user = enrollment.user

            # 각 과목별 완료된 강의 수 계산
            subject_progress = []
            for subject_info in subject_data:
                subject = subject_info["subject"]
                lectures = subject_info["lectures"]

                # 완료된 강의 수
                completed_lectures = LectureProgress.objects.filter(
                    user=user, lecture__subject=subject, is_completed=True
                ).count()

                # 프로젝트 제출물 (중간/기말고사인 경우)
                project_submission = None
                if subject.subject_type in ["midterm", "final"]:
                    project_submission = (
                        ProjectSubmission.objects.filter(user=user, subject=subject)
                        .order_by("-submitted_at")
                        .first()
                    )

                subject_progress.append(
                    {
                        "subject": subject,
                        "completed": completed_lectures,
                        "total": lectures.count(),
                        "percentage": round(
                            (
                                completed_lectures / lectures.count() * 100
                                if lectures.count() > 0
                                else 0
                            ),
                            1,
                        ),
                        "project_submission": project_submission,
                    }
                )

            # 수료증 정보
            certificate = None
            if enrollment.status == "certified":
                try:
                    certificate = Certificate.objects.get(enrollment=enrollment)
                except Certificate.DoesNotExist:
                    pass

            student_progress.append(
                {
                    "user": user,
                    "enrollment": enrollment,
                    "subject_progress": subject_progress,
                    "certificate": certificate,
                }
            )

        context.update(
            {
                "subject_data": subject_data,
                "student_progress": student_progress,
            }
        )

        return context


class CourseAttendanceView(AdminRequiredMixin, DetailView):
    """특정 과정의 출석부 페이지

    특정 과정의 출석부를 보여주는 페이지입니다.
    수강생별로 특정 기간 동안의 일별 학습 활동을 표시합니다.
    기간을 선택하여 다른 주의 출석 현황을 확인할 수 있습니다.
    """

    model = Course
    template_name = "admin_portal/course_progress/attendance.html"
    context_object_name = "course"
    pk_url_kwarg = "course_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.object

        # 과정에 등록된 모든 수강생
        enrollments = (
            Enrollment.objects.filter(course=course)
            .select_related("user")
            .order_by("user__username")
        )

        # 현재 날짜
        today = timezone.now().date()

        # 기간 선택 옵션 생성 (6개월 = 약 26주)
        period_options = []
        # 2주 단위로 생성, 총 26주 = 13개 옵션
        for i in range(13):
            # 현재 주 시작일(월요일)에서 i*2주 이전
            start_date = today - timedelta(days=(today.weekday() + 14 * i))
            end_date = start_date + timedelta(days=13)
            period_value = f"{start_date.isoformat()},{end_date.isoformat()}"
            label = (
                f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
            )
            period_options.append({"value": period_value, "label": label})

        # 요청된 기간 처리
        selected_period = self.request.GET.get("period", period_options[0]["value"])

        try:
            start_date_str, end_date_str = selected_period.split(",")
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except (ValueError, AttributeError):
            # 기본값: 이번주 월요일부터 2주일 (14일)
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=13)

        # 날짜 범위 생성 (항상 14일)
        date_range = []
        current_date = start_date
        for _ in range(14):  # 항상 14일로 고정
            date_range.append(current_date)
            current_date += timedelta(days=1)

        # 수강생별 활동 내역
        attendance_data = []
        for enrollment in enrollments:
            user = enrollment.user

            # 날짜별 활동 여부
            daily_activities = {}
            for day in date_range:
                day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
                day_start = timezone.make_aware(day_start)
                day_end = timezone.datetime.combine(day, timezone.datetime.max.time())
                day_end = timezone.make_aware(day_end)

                # 해당 날짜에 완료한 강의 수
                completed_lectures = LectureProgress.objects.filter(
                    user=user,
                    lecture__subject__course=course,
                    completed_at__range=(day_start, day_end),
                ).count()

                daily_activities[day.isoformat()] = completed_lectures

            attendance_data.append(
                {
                    "user": user,
                    "enrollment": enrollment,
                    "daily_activities": daily_activities,
                }
            )

        context.update(
            {
                "date_range": date_range,
                "attendance_data": attendance_data,
                "period_options": period_options,
                "selected_period": selected_period,
            }
        )

        return context


class CourseAttendancePDFView(AdminRequiredMixin, View):
    """특정 과정의 출석부 PDF 생성

    특정 과정의 출석부를 PDF 파일로 생성하여 다운로드할 수 있게 합니다.
    과정의 시작일부터 현재까지의 전체 기간 데이터를 포함합니다.
    수강생별로 각 날짜의 활동을 보여주며 현재 화면에 표시된 기간은 강조 표시됩니다.
    """

    def get(self, request, course_id, *args, **kwargs):
        course = get_object_or_404(Course, id=course_id)

        # 과정에 등록된 모든 수강생
        enrollments = (
            Enrollment.objects.filter(course=course)
            .select_related("user")
            .order_by("user__username")
        )

        # 현재 날짜
        today = timezone.now().date()

        # 과정의 첫 번째 활동 시작일 확인 (가장 오래된 수강 신청 또는 활동 날짜)
        oldest_enrollment_date = Enrollment.objects.filter(course=course).aggregate(
            Min("enrolled_at")
        )["enrolled_at__min"]

        oldest_activity_date = LectureProgress.objects.filter(
            lecture__subject__course=course
        ).aggregate(Min("created_at"))["created_at__min"]

        # 둘 중 더 오래된 날짜를 시작일로 설정
        if oldest_enrollment_date and oldest_activity_date:
            start_date = min(oldest_enrollment_date.date(), oldest_activity_date.date())
        elif oldest_enrollment_date:
            start_date = oldest_enrollment_date.date()
        elif oldest_activity_date:
            start_date = oldest_activity_date.date()
        else:
            # 데이터가 없는 경우, 기본적으로 3개월 전으로 설정
            start_date = today - timedelta(days=90)

        # 요청에서 넘어온 기간은 현재 화면에 표시할 기간으로만 사용
        selected_period = request.GET.get("period", "")
        display_start_date = None

        try:
            start_date_str, _ = selected_period.split(",")
            display_start_date = date.fromisoformat(start_date_str)
        except (ValueError, AttributeError):
            # 기본값: 이번주 월요일
            display_start_date = today - timedelta(days=today.weekday())

        # 날짜 범위 생성 (시작일부터 오늘까지)
        date_range = []
        current_date = start_date
        while current_date <= today:
            date_range.append(current_date)
            current_date += timedelta(days=1)

        # 출석부 데이터 생성
        attendance_data = []
        for enrollment in enrollments:
            user = enrollment.user

            # 날짜별 활동 여부
            daily_activities = []
            for day in date_range:
                day_start = timezone.datetime.combine(day, timezone.datetime.min.time())
                day_start = timezone.make_aware(day_start)
                day_end = timezone.datetime.combine(day, timezone.datetime.max.time())
                day_end = timezone.make_aware(day_end)

                # 해당 날짜에 완료한 강의 수
                completed_lectures = LectureProgress.objects.filter(
                    user=user,
                    lecture__subject__course=course,
                    completed_at__range=(day_start, day_end),
                ).count()

                daily_activities.append(completed_lectures)

            attendance_data.append(
                [
                    user.username,
                    user.get_full_name() or "-",
                    *daily_activities,
                    enrollment.progress_percentage,
                ]
            )

        # 한글 폰트 등록
        font_path = (
            Path(settings.BASE_DIR) / "static" / "fonts" / "NanumGothic-Regular.ttf"
        )
        # ReportLab에서 한글 지원 폰트 설정
        if font_path.exists():
            pdfmetrics.registerFont(TTFont("NanumGothic", str(font_path)))
            font_name = "NanumGothic"
        else:
            # 파일이 없으면 기본 폰트 사용 (한글이 깨질 수 있음)
            font_name = "Helvetica"

        # PDF 생성 (가로 방향으로)
        buffer = io.BytesIO()

        # A4 가로 크기보다 더 넓은 페이지 사이즈 설정 - 날짜가 많을 경우 적용
        # 날짜 수가 30일 이상일 경우 더 넓은 페이지 사용
        if len(date_range) > 30:
            pagesize = (
                landscape(A4)[0] * 1.5,
                landscape(A4)[1],
            )  # 가로 길이를 1.5배로 확장
        else:
            pagesize = landscape(A4)

        doc = SimpleDocTemplate(
            buffer,
            pagesize=pagesize,
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Heading1"],
            fontName=font_name,
            alignment=TA_CENTER,
            fontSize=16,
            spaceAfter=12,
        )

        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontName=font_name,
            alignment=TA_CENTER,
            fontSize=12,
            spaceAfter=12,
        )

        # 현재 화면에 표시된 기간 하이라이트를 위한 열 인덱스 계산
        highlight_start_idx = None
        highlight_end_idx = None

        if display_start_date:
            # 시작일 + 13일(2주)까지의 인덱스 계산
            display_end_date = display_start_date + timedelta(days=13)

            # 날짜 범위 내 인덱스 찾기
            for i, day in enumerate(date_range):
                if day == display_start_date:
                    highlight_start_idx = i + 2  # username과 fullname 열 이후
                if day == display_end_date:
                    highlight_end_idx = i + 2

        # 표 데이터 생성
        data = [
            # 헤더
            [
                "사용자 ID",
                "이름",
                *[day.strftime("%y/%m/%d") for day in date_range],
                "전체 진행률(%)",
            ],
            # 데이터 행
            *attendance_data,
        ]

        # 표 스타일
        table_style = TableStyle(
            [
                # 기본 스타일
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), font_name),  # 한글 폰트 적용
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
                ("ALIGN", (2, 1), (-2, -1), "CENTER"),  # 날짜 칼럼은 가운데 정렬
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),  # 진행률 칼럼은 오른쪽 정렬
                ("FONTSIZE", (2, 0), (-2, 0), 7),  # 날짜 헤더 칼럼은 더 작은 글씨로
                ("FONTSIZE", (2, 1), (-2, -1), 8),  # 날짜 데이터는 읽기 좋게 약간 키움
                ("FONTNAME", (0, 1), (-1, -1), font_name),  # 데이터 행도 한글 폰트 적용
                ("WORDWRAP", (0, 0), (-1, -1), True),  # 텍스트 자동 줄바꿈 활성화
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),  # 모든 셀 내용 세로 가운데 정렬
                ("TOPPADDING", (0, 0), (-1, -1), 4),  # 위쪽 패딩 추가
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),  # 아래쪽 패딩 추가
            ]
        )

        # 현재 화면에 표시된 기간 하이라이트
        if highlight_start_idx is not None and highlight_end_idx is not None:
            table_style.add(
                "BACKGROUND",
                (highlight_start_idx, 0),
                (highlight_end_idx, 0),
                colors.lightgreen,
            )

        # 컬럼 너비 계산 개선
        username_width = 80  # 사용자 ID 확장
        fullname_width = 80  # 이름 확장
        progress_width = 60  # 진행률 확장

        # 나머지 가용 너비 계산
        available_width = doc.width - (username_width + fullname_width + progress_width)

        # 날짜가 많을 경우 최소 너비 보장하면서 균등 분배
        if date_range:
            date_width = (
                max(30, available_width / len(date_range))
                if len(date_range) > 14
                else available_width / len(date_range)
            )
        else:
            date_width = 30

        col_widths = [username_width, fullname_width]  # 사용자 ID, 이름
        col_widths.extend([date_width] * len(date_range))  # 날짜 열
        col_widths.append(progress_width)  # 진행률 칼럼

        table = Table(data, colWidths=col_widths, repeatRows=1)
        table.setStyle(table_style)

        # 문서 요소
        elements = [
            Paragraph(f"{course.title} - 전체 수강생 출석부", title_style),
            Paragraph(
                f"기간: {start_date.strftime('%Y-%m-%d')} ~ {today.strftime('%Y-%m-%d')} (총 {len(date_range)}일)",
                subtitle_style,
            ),
            Spacer(1, 0.2 * inch),
            table,
        ]

        # PDF 생성
        doc.build(elements)

        # PDF 파일 응답
        buffer.seek(0)
        response = HttpResponse(buffer, content_type="application/pdf")
        filename = f'attendance_{course.title}_full_{today.strftime("%Y%m%d")}.pdf'
        response["Content-Disposition"] = f'attachment; filename="{filename}"'

        return response


class CourseManagementView(AdminRequiredMixin, ListView):
    """과정 관리 메인 페이지

    모든 과정의 목록을 보여주고 검색, 수정, 삭제 기능을 제공합니다.
    각 과정의 수강생 수와 과목 수도 함께 표시합니다.
    """

    model = Course
    template_name = "admin_portal/course_management/course_list.html"
    context_object_name = "courses"
    paginate_by = 10

    def get_queryset(self):
        search_query = self.request.GET.get("search", "")
        if search_query:
            return Course.objects.filter(title__icontains=search_query).order_by(
                "title"
            )
        return Course.objects.all().order_by("title")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 각 과정의 등록된 학생 수와 과목 수 가져오기
        for course in context["courses"]:
            course.student_count = Enrollment.objects.filter(course=course).count()
            course.subject_count = Subject.objects.filter(course=course).count()

        context["search_query"] = self.request.GET.get("search", "")
        return context


class CourseCreateView(AdminRequiredMixin, CreateView):
    """과정 생성 페이지

    새로운 과정을 생성하는 페이지입니다.
    과정 제목, 설명, 난이도, 대상 학생, 학점, 가격 등의 정보를 입력받습니다.
    현재 로그인한 관리자가 자동으로 강사로 설정됩니다.
    """

    model = Course
    template_name = "admin_portal/course_management/course_create.html"
    fields = [
        "title",
        "description",
        "short_description",
        "difficulty_level",
        "target_audience",
        "estimated_time",
        "credit",
        "price",
        "thumbnail_image",
    ]

    def form_valid(self, form):
        # 현재 로그인한 관리자를 강사로 설정
        instructor_profile, created = InstructorProfile.objects.get_or_create(
            user=self.request.user,
            defaults={"bio": "", "experience": "", "qualification": ""},
        )
        form.instance.instructor = instructor_profile

        messages.success(
            self.request,
            f'과정 "{form.instance.title}"이(가) 성공적으로 생성되었습니다.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("admin_portal:course_management")


class CourseDetailView(AdminRequiredMixin, UpdateView):
    """과정 상세 및 수정 페이지

    기존 과정의 상세 정보를 보고 수정할 수 있는 페이지입니다.
    과정 정보 외에도 수강생 수, 과목 수 등의 통계도 함께 보여줍니다.
    """

    model = Course
    template_name = "admin_portal/course_management/course_detail.html"
    context_object_name = "course"
    pk_url_kwarg = "course_id"
    fields = [
        "title",
        "description",
        "short_description",
        "difficulty_level",
        "target_audience",
        "estimated_time",
        "credit",
        "price",
        "thumbnail_image",
    ]

    def form_valid(self, form):
        form.instance.updated_at = timezone.now()
        messages.success(
            self.request,
            f'과정 "{form.instance.title}"이(가) 성공적으로 업데이트되었습니다.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("admin_portal:course_management")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 과정에 등록된 학생 수 및 과목 수
        context["student_count"] = Enrollment.objects.filter(course=self.object).count()
        context["subject_count"] = Subject.objects.filter(course=self.object).count()
        return context


class CourseDeleteView(AdminRequiredMixin, DeleteView):
    """과정 삭제 처리를 담당하는 뷰

    특정 Course 인스턴스를 삭제하며, 성공 시 과정 관리 목록 페이지로 리다이렉트합니다.
    GET 요청은 허용하지 않고 POST 요청만 처리합니다.
    """

    model = Course
    pk_url_kwarg = "course_id"
    success_url = reverse_lazy("admin_portal:course_management")

    # GET 요청은 허용하지 않고 POST 요청만 처리
    def get(self, request, *args, **kwargs):
        return redirect(
            "admin_portal:course_detail", course_id=self.kwargs["course_id"]
        )

    def delete(self, request, *args, **kwargs):
        course = self.get_object()
        title = course.title
        result = super().delete(request, *args, **kwargs)
        messages.success(request, f'과정 "{title}"이(가) 성공적으로 삭제되었습니다.')
        return result


class SubjectManagementView(AdminRequiredMixin, ListView):
    """과목 관리 페이지

    특정 과정에 포함된 과목 목록을 보여주고 관리할 수 있는 페이지입니다.
    각 과목의 유형(일반, 중간고사, 기말고사)과 강의 수를 표시합니다.
    """

    model = Subject
    template_name = "admin_portal/course_management/subject_list.html"
    context_object_name = "subjects"

    def get_queryset(self):
        course_id = self.kwargs.get("course_id")
        return Subject.objects.filter(course_id=course_id).order_by("order_index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        context["course"] = get_object_or_404(Course, id=course_id)

        # 각 과목의 강의 수 가져오기
        for subject in context["subjects"]:
            subject.lecture_count = (
                Lecture.objects.filter(subject=subject).count()
                if subject.subject_type == "normal"
                else 0
            )

        return context


class SubjectCreateView(AdminRequiredMixin, CreateView):
    """과목 생성 페이지 뷰

    특정 과정에 새로운 과목을 생성하는 페이지입니다.
    과목 제목, 설명, 유형(일반, 중간고사, 기말고사), 순서 등을 입력받습니다.
    기본 순서 인덱스는 현재 과목 수 + 1로 설정됩니다.
    """

    model = Subject
    template_name = "admin_portal/course_management/subject_create.html"
    fields = ["title", "description", "subject_type", "order_index"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        context["course"] = get_object_or_404(Course, id=course_id)

        # 현재 과목 수 가져오기 (기본 순서 인덱스 설정용)
        current_subject_count = Subject.objects.filter(course_id=course_id).count()
        context["next_order_index"] = current_subject_count + 1

        return context

    def form_valid(self, form):
        course_id = self.kwargs.get("course_id")
        form.instance.course = get_object_or_404(Course, id=course_id)
        messages.success(
            self.request,
            f'과목 "{form.instance.title}"이(가) 성공적으로 생성되었습니다.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "admin_portal:subject_management",
            kwargs={"course_id": self.kwargs.get("course_id")},
        )


class SubjectDetailView(AdminRequiredMixin, UpdateView):
    """과목 상세 및 수정 페이지

    기존 과목의 상세 정보를 보고 수정할 수 있는 페이지입니다.
    과목 정보를 업데이트하거나 삭제할 수 있는 기능을 제공합니다.
    과목에 포함된 강의 수도 표시합니다.
    """

    model = Subject
    template_name = "admin_portal/course_management/subject_detail.html"
    context_object_name = "subject"
    pk_url_kwarg = "subject_id"
    fields = ["title", "description", "subject_type", "order_index"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        context["course"] = get_object_or_404(Course, id=course_id)

        # 과목의 강의 수
        context["lecture_count"] = Lecture.objects.filter(subject=self.object).count()

        return context

    def form_valid(self, form):
        messages.success(
            self.request,
            f'과목 "{form.instance.title}"이(가) 성공적으로 업데이트되었습니다.',
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "admin_portal:subject_management",
            kwargs={"course_id": self.kwargs.get("course_id")},
        )

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "delete":
            subject = self.get_object()
            title = subject.title
            course_id = subject.course.id
            subject.delete()
            messages.success(
                request, f'과목 "{title}"이(가) 성공적으로 삭제되었습니다.'
            )
            return redirect("admin_portal:subject_management", course_id=course_id)

        return super().post(request, *args, **kwargs)


class LectureManagementView(AdminRequiredMixin, ListView):
    """강의 관리 페이지

    특정 과목에 포함된 강의 목록을 보여주고 관리할 수 있는 페이지입니다.
    각 강의의 유형(동영상, 미션), 순서, 내용 등을 확인할 수 있습니다.
    """

    model = Lecture
    template_name = "admin_portal/course_management/lecture_list.html"
    context_object_name = "lectures"

    def get_queryset(self):
        subject_id = self.kwargs.get("subject_id")
        return Lecture.objects.filter(subject_id=subject_id).order_by("order_index")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        subject_id = self.kwargs.get("subject_id")

        context["course"] = get_object_or_404(Course, id=course_id)
        context["subject"] = get_object_or_404(
            Subject, id=subject_id, course_id=course_id
        )

        return context


class LectureCreateView(AdminRequiredMixin, CreateView):
    """강의 생성 페이지

    특정 과목에 새로운 강의를 생성하는 페이지입니다.
    강의 제목, 설명, 유형(동영상 또는 미션), 순서 등을 입력받습니다.
    미션 강의인 경우 퀴즈 문제를 추가할 수 있습니다.
    """

    model = Lecture
    template_name = "admin_portal/course_management/lecture_create.html"
    fields = ["title", "description", "lecture_type", "order_index", "video_file"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        subject_id = self.kwargs.get("subject_id")

        context["course"] = get_object_or_404(Course, id=course_id)
        context["subject"] = get_object_or_404(
            Subject, id=subject_id, course_id=course_id
        )

        # 기본 순서 인덱스 설정
        current_lecture_count = Lecture.objects.filter(subject_id=subject_id).count()
        context["next_order_index"] = current_lecture_count + 1

        return context

    def form_valid(self, form):
        subject_id = self.kwargs.get("subject_id")
        form.instance.subject = get_object_or_404(Subject, id=subject_id)

        # 폼 저장
        response = super().form_valid(form)
        lecture = self.object

        # 미션(퀴즈) 강의인 경우 문제 처리
        if lecture.lecture_type == "mission" and "questions" in self.request.POST:
            questions_data = json.loads(self.request.POST.get("questions"))

            for i, q_data in enumerate(questions_data):
                question_text = q_data.get("question_text", q_data.get("text", ""))
                question = MissionQuestion(
                    lecture=lecture,
                    question_text=question_text,
                    option1=q_data["options"][0],
                    option2=q_data["options"][1],
                    option3=q_data["options"][2],
                    option4=q_data["options"][3],
                    option5=q_data["options"][4],
                    correct_answer=q_data["correct_answer"],
                    order_index=q_data.get("order_index", i + 1),
                )
                question.save()

        messages.success(
            self.request, f'강의 "{lecture.title}"이(가) 성공적으로 생성되었습니다.'
        )
        return response

    def get_success_url(self):
        return reverse(
            "admin_portal:lecture_management",
            kwargs={
                "course_id": self.kwargs.get("course_id"),
                "subject_id": self.kwargs.get("subject_id"),
            },
        )


class LectureDetailView(AdminRequiredMixin, UpdateView):
    """강의 상세 및 수정 페이지

    기존 강의의 상세 정보를 보고 수정할 수 있는 페이지입니다.
    강의 정보를 업데이트하거나 삭제할 수 있는 기능을 제공합니다.
    미션 강의인 경우 퀴즈 문제를 관리할 수 있습니다.
    """

    model = Lecture
    template_name = "admin_portal/course_management/lecture_detail.html"
    context_object_name = "lecture"
    pk_url_kwarg = "lecture_id"
    fields = ["title", "description", "order_index", "video_file"]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course_id = self.kwargs.get("course_id")
        subject_id = self.kwargs.get("subject_id")

        context["course"] = get_object_or_404(Course, id=course_id)
        context["subject"] = get_object_or_404(
            Subject, id=subject_id, course_id=course_id
        )

        # 퀴즈 강의인 경우 문제 목록 가져오기
        if self.object.lecture_type == "mission":
            context["questions"] = MissionQuestion.objects.filter(lecture=self.object)

        return context

    def form_valid(self, form):
        # 강의 업데이트
        response = super().form_valid(form)
        lecture = self.object

        # 미션(퀴즈) 강의인 경우 문제 업데이트
        if lecture.lecture_type == "mission" and "questions" in self.request.POST:
            # 기존 문제 삭제
            MissionQuestion.objects.filter(lecture=lecture).delete()

            # 새 문제 추가
            questions_data = json.loads(self.request.POST.get("questions"))

            for i, q_data in enumerate(questions_data):
                question_text = q_data.get("question_text", q_data.get("text", ""))
                question = MissionQuestion(
                    lecture=lecture,
                    question_text=question_text,
                    option1=q_data["options"][0],
                    option2=q_data["options"][1],
                    option3=q_data["options"][2],
                    option4=q_data["options"][3],
                    option5=q_data["options"][4],
                    correct_answer=q_data["correct_answer"],
                    order_index=q_data.get("order_index", i + 1),
                )
                question.save()

        messages.success(
            self.request, f'강의 "{lecture.title}"이(가) 성공적으로 업데이트되었습니다.'
        )
        return response

    def get_success_url(self):
        return reverse(
            "admin_portal:lecture_management",
            kwargs={
                "course_id": self.kwargs.get("course_id"),
                "subject_id": self.kwargs.get("subject_id"),
            },
        )

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")

        if action == "delete":
            lecture = self.get_object()
            title = lecture.title
            course_id = lecture.subject.course.id
            subject_id = lecture.subject.id
            lecture.delete()
            messages.success(
                request, f'강의 "{title}"이(가) 성공적으로 삭제되었습니다.'
            )
            return redirect(
                "admin_portal:lecture_management",
                course_id=course_id,
                subject_id=subject_id,
            )

        return super().post(request, *args, **kwargs)


class UserLearningRecordsView(AdminRequiredMixin, TemplateView):
    """사용자 학습 기록 페이지

    사용자별 학습 기록을 볼 수 있는 페이지입니다.
    특정 날짜의 학습 활동, 각 사용자의 과정별 진행 상황을 확인할 수 있습니다.
    사용자 필터링과 날짜 필터링 기능을 제공합니다.
    """

    template_name = "admin_portal/user_learning_records.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 모든 학생 사용자 목록 (관리자 제외)
        context["all_users"] = User.objects.filter(is_admin=False).order_by("username")

        # 필터링 옵션
        selected_user_id = self.request.GET.get("user_id")
        selected_date_str = self.request.GET.get("date")

        # 날짜 필터링 (기본값: 오늘)
        today = timezone.now().date()

        try:
            selected_date = (
                date.fromisoformat(selected_date_str) if selected_date_str else today
            )
        except ValueError:
            selected_date = today

        context["selected_date"] = selected_date

        # 사용자 필터링
        selected_user = None
        enrolled_courses_count = 0
        completed_courses_count = 0
        avg_progress = 0

        if selected_user_id:
            try:
                selected_user = User.objects.get(id=selected_user_id)
                # 수강 중인 과정 수
                enrollments = Enrollment.objects.filter(user=selected_user)
                enrolled_courses_count = enrollments.count()

                # 완료한 과정 수
                completed_courses_count = enrollments.filter(
                    status__in=["completed", "certified"]
                ).count()

                # 평균 진행률
                if enrolled_courses_count > 0:
                    avg_progress = (
                        enrollments.aggregate(Avg("progress_percentage"))[
                            "progress_percentage__avg"
                        ]
                        or 0
                    )
            except User.DoesNotExist:
                selected_user = None

        context["selected_user"] = selected_user
        context["selected_user_id"] = (
            int(selected_user_id)
            if selected_user_id and selected_user_id.isdigit()
            else None
        )
        context["enrolled_courses_count"] = enrolled_courses_count
        context["completed_courses_count"] = completed_courses_count
        context["avg_progress"] = avg_progress

        # 일간 영상 시청 현황 데이터
        daily_activities_query = (
            LectureProgress.objects.select_related(
                "user", "lecture", "lecture__subject", "lecture__subject__course"
            )
            .filter(
                is_completed=True,
                completed_at__date=selected_date,
            )
            .order_by("-completed_at")
        )  # 최근 활동이 상단에 오도록 변경

        # 특정 사용자에 대한 필터링
        if selected_user:
            daily_activities_query = daily_activities_query.filter(user=selected_user)
            # 해당 사용자의 모든 수강 신청
            enrollments = (
                Enrollment.objects.filter(user=selected_user)
                .select_related("course")
                .order_by("-enrolled_at")
            )
        else:
            # 모든 사용자의 수강 신청 (최근 50개)
            enrollments = (
                Enrollment.objects.all()
                .select_related("user", "course")
                .order_by("-last_activity_at")[:50]
            )

        context["enrollments"] = enrollments

        # 페이지네이션 적용
        paginator = Paginator(daily_activities_query, 20)  # 페이지당 20개 항목
        page = self.request.GET.get("page")

        try:
            daily_activities = paginator.page(page)
        except PageNotAnInteger:
            # 페이지가 정수가 아니면 첫 페이지
            daily_activities = paginator.page(1)
        except EmptyPage:
            # 페이지가 범위를 벗어나면 마지막 페이지
            daily_activities = paginator.page(paginator.num_pages)

        context["daily_activities"] = daily_activities

        return context


class PaymentManagementView(AdminRequiredMixin, ListView):
    """결제 내역 관리 페이지

    결제 내역을 조회하고 관리할 수 있는 페이지입니다.
    결제 상태, 기간, 사용자 등으로 필터링할 수 있으며,
    매출 통계 및 결제 방법별 비율 차트를 제공합니다.
    """

    model = Payment
    template_name = "admin_portal/payments/payment_list.html"
    context_object_name = "payments"
    paginate_by = 20

    def get_queryset(self):
        # 검색 및 필터링
        search_query = self.request.GET.get("search", "")
        status_filter = self.request.GET.get("status", "all")
        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")

        # 기본 쿼리셋 생성
        queryset = Payment.objects.all().select_related("user", "course")

        # 상태 필터 적용
        if status_filter != "all":
            queryset = queryset.filter(payment_status=status_filter)

        # 검색 필터 적용
        if search_query:
            queryset = queryset.filter(
                Q(user__username__icontains=search_query)
                | Q(user__email__icontains=search_query)
                | Q(course__title__icontains=search_query)
                | Q(merchant_uid__icontains=search_query)
            )

        # 날짜 필터링
        if date_from:
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                queryset = queryset.filter(created_at__date__gte=date_from)
            except ValueError:
                pass

        if date_to:
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                queryset = queryset.filter(created_at__date__lte=date_to)
            except ValueError:
                pass

        # 정렬
        return queryset.order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 검색 및 필터링 파라미터 유지
        context["search_query"] = self.request.GET.get("search", "")
        context["status_filter"] = self.request.GET.get("status", "all")

        date_from = self.request.GET.get("date_from", "")
        date_to = self.request.GET.get("date_to", "")

        if date_from:
            try:
                date_from = datetime.strptime(date_from, "%Y-%m-%d").date()
                context["date_from"] = date_from.strftime("%Y-%m-%d")
            except ValueError:
                context["date_from"] = ""
        else:
            context["date_from"] = ""

        if date_to:
            try:
                date_to = datetime.strptime(date_to, "%Y-%m-%d").date()
                context["date_to"] = date_to.strftime("%Y-%m-%d")
            except ValueError:
                context["date_to"] = ""
        else:
            context["date_to"] = ""

        # 통계 데이터
        payments = Payment.objects.all()
        context["completed_count"] = payments.filter(payment_status="completed").count()
        context["total_sales"] = (
            payments.filter(payment_status="completed").aggregate(Sum("amount"))[
                "amount__sum"
            ]
            or 0
        )
        context["today_sales"] = (
            payments.filter(
                payment_status="completed", created_at__date=timezone.now().date()
            ).aggregate(Sum("amount"))["amount__sum"]
            or 0
        )

        # 최근 7일 매출 추이
        today = timezone.now().date()
        daily_sales = []
        daily_dates = []

        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            daily_dates.append(date.strftime("%m/%d"))

            day_sales = (
                payments.filter(
                    payment_status="completed", created_at__date=date
                ).aggregate(Sum("amount"))["amount__sum"]
                or 0
            )

            daily_sales.append(day_sales)

        context["daily_dates"] = json.dumps(daily_dates)
        context["daily_sales"] = json.dumps(daily_sales)

        # 결제 방법별 비율
        context["payment_methods"] = (
            payments.filter(payment_status="completed")
            .values("payment_method")
            .annotate(count=Count("id"), sum=Sum("amount"))
            .order_by("-sum")
        )

        return context


class PaymentDetailAdminView(AdminRequiredMixin, DetailView):
    """결제 상세 관리 페이지

    특정 결제 내역의 상세 정보를 보여주는 페이지입니다.
    결제 정보, 구매 상품 정보, 구매자 정보 등을 확인할 수 있으며,
    완료된 결제의 경우 환불 처리를 할 수 있습니다.
    """

    model = Payment
    template_name = "admin_portal/payments/payment_detail.html"
    context_object_name = "payment"
    pk_url_kwarg = "payment_id"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment = self.get_object()

        # 익명화된 사용자 정보 처리
        if payment.is_anonymized:
            try:
                deleted_user = DeletedUserData.objects.get(
                    original_user_id=payment.anonymized_user_id
                )
                context["anonymized_user"] = deleted_user
            except DeletedUserData.DoesNotExist:
                context["anonymized_user"] = None

        return context

    def post(self, request, *args, **kwargs):
        payment = self.get_object()

        # 환불 처리
        if "refund" in request.POST:
            refund_reason = request.POST.get(
                "refund_reason", "관리자 환불 처리"
            ).strip()

            try:
                with transaction.atomic():
                    # 포트원 API 호출하여 환불 처리
                    is_successful, result = payment_client.refund_payment(
                        reason=refund_reason,
                        imp_uid=payment.imp_uid,
                        merchant_uid=payment.merchant_uid,
                        amount=payment.amount,
                    )

                    if is_successful:
                        # 환불 성공 시 결제 정보 업데이트
                        payment.refund_reason = refund_reason
                        payment.payment_status = "refunded"
                        payment.updated_at = timezone.now()
                        payment.save()

                        # 수강 등록 정보도 삭제
                        Enrollment.objects.filter(
                            user=payment.user, course=payment.course
                        ).delete()

                        messages.success(request, "환불이 성공적으로 처리되었습니다.")
                    else:
                        messages.error(
                            request, f"환불 처리 중 오류가 발생했습니다: {result}"
                        )

            except Exception as e:
                logger.exception("환불 처리 중 오류 발생")
                messages.error(request, f"환불 처리 중 오류가 발생했습니다: {str(e)}")

        return redirect("admin_portal:payment_detail", payment_id=payment.id)
        context = super().get_context_data(**kwargs)
        payment = self.get_object()

        # 익명화된 사용자 정보 처리
        if payment.is_anonymized:
            try:
                deleted_user = DeletedUserData.objects.get(
                    original_user_id=payment.anonymized_user_id
                )
                context["anonymized_user"] = deleted_user
            except DeletedUserData.DoesNotExist:
                context["anonymized_user"] = None

        return context


class ManageStudentEnrollmentView(AdminRequiredMixin, TemplateView):
    """관리자가 학생의 과정 등록/취소 관리

    관리자가 학생들의 과정 등록 및 취소를 관리할 수 있는 페이지입니다.
    특정 학생을 특정 과정에 수동으로 등록하거나 등록을 취소할 수 있습니다.
    """

    template_name = "admin_portal/manage_enrollment.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 현재 등록된 내역 가져오기
        context["enrollments"] = (
            Enrollment.objects.all()
            .select_related("user", "course")
            .order_by("-enrolled_at")
        )

        # 사용자 및 과정 목록 가져오기
        context["users"] = User.objects.filter(is_admin=False).order_by("username")
        context["courses"] = Course.objects.all().order_by("title")

        return context

    def post(self, request, *args, **kwargs):
        action = request.POST.get("action")
        user_id = request.POST.get("user_id")
        course_id = request.POST.get("course_id")

        try:
            user = User.objects.get(id=user_id)
            course = Course.objects.get(id=course_id)

            if action == "enroll":
                # 등록 처리
                enrollment, created = Enrollment.objects.get_or_create(
                    user=user,
                    course=course,
                    defaults={"status": "enrolled", "progress_percentage": 0},
                )

                if created:
                    logger.info(
                        f"Admin {request.user.username} enrolled user {user.username} in course {course.title}"
                    )
                    messages.success(
                        request,
                        f"{user.username}님을 {course.title} 과정에 성공적으로 등록했습니다.",
                    )
                else:
                    logger.info(
                        f"Admin {request.user.username} attempted to enroll user {user.username} who is already enrolled in course {course.title}"
                    )
                    messages.info(
                        request,
                        f"{user.username}님은 이미 {course.title} 과정에 등록되어 있습니다.",
                    )

            elif action == "unenroll":
                # 등록 취소 처리
                deleted, _ = Enrollment.objects.filter(
                    user=user, course=course
                ).delete()
                if deleted:
                    logger.info(
                        f"Admin {request.user.username} unenrolled user {user.username} from course {course.title}"
                    )
                    messages.success(
                        request,
                        f"{user.username}님의 {course.title} 과정 등록이 취소되었습니다.",
                    )
                else:
                    logger.warning(
                        f"Admin {request.user.username} attempted to unenroll user {user.username} who is not enrolled in course {course.title}"
                    )
                    messages.info(
                        request,
                        f"{user.username}님은 {course.title} 과정에 등록되어 있지 않습니다.",
                    )

        except (User.DoesNotExist, Course.DoesNotExist):
            logger.error(
                f"Enrollment management error: user_id={user_id}, course_id={course_id} not found"
            )
            messages.error(request, "사용자 또는 과정을 찾을 수 없습니다.")

        return redirect("admin_portal:manage_enrollment")
