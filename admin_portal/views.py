from django.shortcuts import get_object_or_404, render, redirect
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q, Min
from django.db.models.functions import TruncWeek
from datetime import timedelta, date
import json
import io
from pathlib import Path
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from accounts.models import User, InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion
from learning.models import Enrollment, Certificate, LectureProgress, ProjectSubmission
from .models import DailyStatistics


@login_required
def admin_dashboard(request):
    """관리자 대시보드 메인 뷰"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")  # 일반 사용자 대시보드로 리디렉션

    # 오늘 날짜
    today = timezone.now().date()

    # 통계 업데이트 (또는 cron job으로 자동화할 수 있음)
    DailyStatistics.update_daily_statistics()

    # 전체 통계 데이터
    total_students = User.objects.filter(is_admin=False).count()
    total_courses = Course.objects.count()
    total_enrollments = Enrollment.objects.count()
    total_certificates = Certificate.objects.count()
    total_video_views = LectureProgress.objects.filter(is_completed=True).count()

    # 최근 30일간 통계
    last_30_days = today - timedelta(days=30)
    daily_stats = DailyStatistics.objects.filter(date__gte=last_30_days).order_by(
        "date"
    )

    # 과정별 수강생 수
    course_enrollments = (
        Course.objects.annotate(student_count=Count("enrollments"))
        .values("title", "student_count")
        .order_by("-student_count")[:10]
    )

    # 평균 평점이 높은 과정
    top_rated_courses = (
        Course.objects.annotate(avg_rating=Avg("reviews__rating"))
        .filter(avg_rating__isnull=False)
        .values("title", "avg_rating")
        .order_by("-avg_rating")[:5]
    )

    # 최근 등록 사용자
    recent_users = User.objects.order_by("-date_joined")[:10]

    # 최근 수강 신청
    recent_enrollments = Enrollment.objects.select_related("user", "course").order_by(
        "-enrolled_at"
    )[:10]

    # 평가 대기 중인 프로젝트
    pending_projects = (
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

    # 차트 데이터 JSON 형식으로 변환
    chart_data = {
        "dates": dates,
        "new_users": new_users_data,
        "active_users": active_users_data,
        "new_enrollments": new_enrollments_data,
        "completed_lectures": video_views_data,
    }

    context = {
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "total_certificates": total_certificates,
        "total_video_views": total_video_views,
        "course_enrollments": course_enrollments,
        "top_rated_courses": top_rated_courses,
        "recent_users": recent_users,
        "recent_enrollments": recent_enrollments,
        "pending_projects": pending_projects,
        "chart_data": json.dumps(chart_data),
        "today_stats": DailyStatistics.objects.filter(date=today).first(),
    }

    return render(request, "admin_portal/dashboard.html", context)


@login_required
def admin_statistics_api(request):
    """대시보드 통계 데이터 API (AJAX 요청용)"""
    if not request.user.is_admin:
        return JsonResponse({"error": "권한이 없습니다."}, status=403)

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
    }

    return JsonResponse(data)


@login_required
def admin_pending_projects(request):
    """평가 대기 중인 프로젝트 목록 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")  # 일반 사용자 대시보드로 리디렉션

    # 검색 및 필터링
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "pending")

    # 기본 쿼리셋 생성
    projects = ProjectSubmission.objects.select_related(
        "user", "subject", "subject__course"
    )

    # 상태 필터 적용
    if status_filter == "all":
        pass  # 모든 프로젝트 표시
    elif status_filter == "pending":
        projects = projects.filter(is_passed=False, reviewed_at__isnull=True)
    elif status_filter == "reviewed":
        projects = projects.filter(reviewed_at__isnull=False)
    elif status_filter == "passed":
        projects = projects.filter(is_passed=True)

    # 검색 필터 적용
    if search_query:
        projects = projects.filter(
            Q(user__username__icontains=search_query)
            | Q(subject__title__icontains=search_query)
            | Q(subject__course__title__icontains=search_query)
        )

    # 정렬
    projects = projects.order_by("-submitted_at")

    # 페이지네이션
    paginator = Paginator(projects, 10)  # 한 페이지에 10개씩 표시
    page = request.GET.get("page")

    try:
        projects_page = paginator.page(page)
    except PageNotAnInteger:
        projects_page = paginator.page(1)
    except EmptyPage:
        projects_page = paginator.page(paginator.num_pages)

    context = {
        "projects": projects_page,
        "search_query": search_query,
        "status_filter": status_filter,
    }

    return render(request, "admin_portal/pending_projects.html", context)


@login_required
def project_detail(request, project_id):
    """프로젝트 제출 상세 보기"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    project = get_object_or_404(ProjectSubmission, id=project_id)

    context = {
        "project": project,
        "subject": project.subject,
        "course": project.subject.course,
    }

    return render(request, "admin_portal/project_detail.html", context)


@login_required
def evaluate_project(request, project_id):
    """프로젝트 평가 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    project = get_object_or_404(ProjectSubmission, id=project_id)

    if request.method == "POST":
        # 평가 처리
        is_passed = request.POST.get("is_passed") == "true"
        feedback = request.POST.get("feedback", "")

        project.is_passed = is_passed
        project.feedback = feedback
        project.reviewed_at = timezone.now()
        project.reviewed_by = request.user
        project.save()

        messages.success(request, "프로젝트 평가가 완료되었습니다.")

        # 학생이 이 프로젝트를 통과했다면 해당 과목의 진행 상태 업데이트
        if is_passed:
            try:
                # 해당 과목(중간/기말고사)에 대한 진행 상태 체크
                enrollment = Enrollment.objects.get(
                    user=project.user, course=project.subject.course
                )

                # 과정 완료 여부 확인
                enrollment.check_completion()

                # 만약 이 프로젝트로 인해 과정이 완료되었다면
                if enrollment.status == "completed":
                    messages.info(
                        request,
                        f"{project.user.username}님의 과정 완료 처리가 되었습니다.",
                    )
            except Enrollment.DoesNotExist:
                pass

        return redirect("admin_portal_project_detail", project_id=project.id)

    context = {
        "project": project,
        "subject": project.subject,
        "course": project.subject.course,
    }

    return render(request, "admin_portal/evaluate_project.html", context)


@login_required
def course_progress_overview(request):
    """과정 진행 상황 개요 페이지"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")

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

    context = {
        "courses_progress": courses_progress,
        "weekly_certificate_data": json.dumps(weekly_data),
        "top_students": top_students,
    }

    return render(request, "admin_portal/course_progress/overview.html", context)


@login_required
def course_progress_detail(request, course_id):
    """특정 과정의 상세 진행 상황 페이지"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)

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

    context = {
        "course": course,
        "subject_data": subject_data,
        "student_progress": student_progress,
    }

    return render(request, "admin_portal/course_progress/detail.html", context)


@login_required
def course_attendance(request, course_id):
    """특정 과정의 출석부 페이지"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)

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
        label = f"{start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}"
        period_options.append({"value": period_value, "label": label})

    # 요청된 기간 처리
    selected_period = request.GET.get("period", period_options[0]["value"])

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

    context = {
        "course": course,
        "date_range": date_range,
        "attendance_data": attendance_data,
        "period_options": period_options,
        "selected_period": selected_period,
    }

    return render(request, "admin_portal/course_progress/attendance.html", context)


@login_required
def course_attendance_pdf(request, course_id):
    """특정 과정의 출석부 PDF 생성 - 시작일부터 현재까지의 전체 기간 포함"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")

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
    font_path = Path(settings.BASE_DIR) / "static" / "fonts" / "NanumGothic-Regular.ttf"
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
    # 날짜 수에 따라 동적으로 페이지 및 셀 너비 조정
    date_count = len(date_range)

    # 사용자 ID와 이름은 고정된 너비로, 진행률은 고정, 날짜 칼럼은 균등 분배
    username_width = 80  # 사용자 ID 확장
    fullname_width = 80  # 이름 확장
    progress_width = 60  # 진행률 확장

    # 나머지 가용 너비 계산
    available_width = doc.width - (username_width + fullname_width + progress_width)

    # 날짜가 많을 경우 최소 너비 보장하면서 균등 분배
    if date_count > 0:
        # 날짜 수가 적을 때는 더 넓게, 많을 때는 최소 너비 보장
        if date_count <= 14:
            date_width = available_width / date_count
        else:
            # 최소 너비 30으로 설정하여 숫자가 잘 보이도록 함
            date_width = max(30, available_width / date_count)
    else:
        date_width = 30

    col_widths = [username_width, fullname_width]  # 사용자 ID, 이름
    col_widths.extend([date_width] * date_count)  # 날짜 열
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


# 과정 관리 관련 뷰 함수
@login_required
def course_management(request):
    """과정 관리 메인 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    # 검색 기능
    search_query = request.GET.get("search", "")
    if search_query:
        courses = Course.objects.filter(title__icontains=search_query)
    else:
        courses = Course.objects.all().order_by("title")

    # 페이지네이션
    paginator = Paginator(courses, 10)  # 한 페이지에 10개씩 표시
    page = request.GET.get("page")

    try:
        courses_page = paginator.page(page)
    except PageNotAnInteger:
        courses_page = paginator.page(1)
    except EmptyPage:
        courses_page = paginator.page(paginator.num_pages)

    # 각 과정의 등록된 학생 수와 과목 수 가져오기
    for course in courses_page:
        course.student_count = Enrollment.objects.filter(course=course).count()
        course.subject_count = Subject.objects.filter(course=course).count()

    context = {
        "courses": courses_page,
        "search_query": search_query,
    }

    return render(request, "admin_portal/course_management/course_list.html", context)


@login_required
def course_create(request):
    """과정 생성 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    if request.method == "POST":
        # 폼 데이터 처리
        title = request.POST.get("title")
        description = request.POST.get("description")
        difficulty = request.POST.get("difficulty")
        target_audience = request.POST.get("target_audience")
        estimated_time = request.POST.get("estimated_time")
        credits = request.POST.get("credits")
        price = request.POST.get("price")
        instructor_profile, created = InstructorProfile.objects.get_or_create(
            user=request.user,
            defaults={"bio": "", "experience": "", "qualification": ""},
        )

        # 과정 생성
        course = Course(
            title=title,
            description=description,
            difficulty_level=difficulty,
            target_audience=target_audience,
            estimated_time=estimated_time,
            credit=credits,
            price=price,
            instructor=instructor_profile,
        )

        # 썸네일 이미지 처리
        if "thumbnail" in request.FILES:
            course.thumbnail_image = request.FILES["thumbnail"]

        course.save()
        messages.success(request, f'과정 "{title}"이(가) 성공적으로 생성되었습니다.')
        return redirect("admin_portal_course_management")

    return render(request, "admin_portal/course_management/course_create.html")


@login_required
def course_detail(request, course_id):
    """과정 상세 및 수정 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        # 과정 업데이트
        course.title = request.POST.get("title")
        course.description = request.POST.get("description")
        course.difficulty = request.POST.get("difficulty")
        course.target_audience = request.POST.get("target_audience")
        course.estimated_time = request.POST.get("estimated_time")
        course.credits = request.POST.get("credits")
        course.price = request.POST.get("price")

        # 썸네일 이미지 처리
        if "thumbnail" in request.FILES:
            course.thumbnail = request.FILES["thumbnail"]

        course.updated_at = timezone.now()
        course.save()

        messages.success(
            request, f'과정 "{course.title}"이(가) 성공적으로 업데이트되었습니다.'
        )
        return redirect("admin_portal_course_management")

    # 과정에 등록된 학생 수 및 과목 수
    student_count = Enrollment.objects.filter(course=course).count()
    subject_count = Subject.objects.filter(course=course).count()

    context = {
        "course": course,
        "student_count": student_count,
        "subject_count": subject_count,
    }

    return render(request, "admin_portal/course_management/course_detail.html", context)


@login_required
def course_delete(request, course_id):
    """과정 삭제 처리"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        title = course.title
        course.delete()
        messages.success(request, f'과정 "{title}"이(가) 성공적으로 삭제되었습니다.')
        return redirect("admin_portal_course_management")

    # GET 요청은 허용하지 않음
    return redirect("admin_portal_course_detail", course_id=course.id)


# 과목 관리 관련 뷰 함수
@login_required
def subject_management(request, course_id):
    """과목 관리 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)
    subjects = Subject.objects.filter(course=course).order_by("order_index")

    # 각 과목의 강의 수 가져오기
    for subject in subjects:
        subject.lecture_count = Lecture.objects.filter(subject=subject).count()

    context = {
        "course": course,
        "subjects": subjects,
    }

    return render(request, "admin_portal/course_management/subject_list.html", context)


@login_required
def subject_create(request, course_id):
    """과목 생성 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)

    if request.method == "POST":
        # 폼 데이터 처리
        title = request.POST.get("title")
        description = request.POST.get("description")
        subject_type = request.POST.get("subject_type")
        order_index = request.POST.get("order_index")

        # 과목 생성
        subject = Subject(
            course=course,
            title=title,
            description=description,
            subject_type=subject_type,
            order_index=order_index,
        )
        subject.save()

        messages.success(request, f'과목 "{title}"이(가) 성공적으로 생성되었습니다.')
        return redirect("admin_portal_subject_management", course_id=course.id)

    # 현재 과목 수 가져오기 (기본 순서 인덱스 설정용)
    current_subject_count = Subject.objects.filter(course=course).count()

    context = {
        "course": course,
        "next_order_index": current_subject_count + 1,
    }

    return render(
        request, "admin_portal/course_management/subject_create.html", context
    )


@login_required
def subject_detail(request, course_id, subject_id):
    """과목 상세 및 수정 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update":
            # 과목 업데이트
            subject.title = request.POST.get("title")
            subject.description = request.POST.get("description")
            subject.subject_type = request.POST.get("subject_type")
            subject.order_index = request.POST.get("order_index")
            subject.save()

            messages.success(
                request, f'과목 "{subject.title}"이(가) 성공적으로 업데이트되었습니다.'
            )

        elif action == "delete":
            # 과목 삭제
            title = subject.title
            subject.delete()
            messages.success(
                request, f'과목 "{title}"이(가) 성공적으로 삭제되었습니다.'
            )
            return redirect("admin_portal_subject_management", course_id=course.id)

        return redirect("admin_portal_subject_management", course_id=course.id)

    # 과목의 강의 수 가져오기
    lecture_count = Lecture.objects.filter(subject=subject).count()

    context = {
        "course": course,
        "subject": subject,
        "lecture_count": lecture_count,
    }

    return render(
        request, "admin_portal/course_management/subject_detail.html", context
    )


# 강의 관리 관련 뷰 함수
@login_required
def lecture_management(request, course_id, subject_id):
    """강의 관리 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lectures = Lecture.objects.filter(subject=subject).order_by("order_index")

    context = {
        "course": course,
        "subject": subject,
        "lectures": lectures,
    }

    return render(request, "admin_portal/course_management/lecture_list.html", context)


@login_required
def lecture_create(request, course_id, subject_id):
    """강의 생성 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)

    if request.method == "POST":
        # 폼 데이터 처리
        title = request.POST.get("title")
        description = request.POST.get("description")
        lecture_type = request.POST.get("lecture_type")
        order_index = request.POST.get("order_index")

        # 강의 생성
        lecture = Lecture(
            subject=subject,
            title=title,
            description=description,
            lecture_type=lecture_type,
            order_index=order_index,
        )

        # 동영상 강의인 경우 비디오 파일 처리
        if lecture_type == "video" and "video_file" in request.FILES:
            lecture.video_file = request.FILES["video_file"]

        lecture.save()

        # 미션(퀴즈) 강의인 경우 문제 처리
        if lecture_type == "quiz" and "questions" in request.POST:
            questions_data = json.loads(request.POST.get("questions"))

            for q_data in questions_data:
                question = MissionQuestion(
                    lecture=lecture,
                    text=q_data["text"],
                    option1=q_data["options"][0],
                    option2=q_data["options"][1],
                    option3=q_data["options"][2],
                    option4=q_data["options"][3],
                    option5=q_data["options"][4],
                    correct_answer=q_data["correct_answer"],
                )
                question.save()

        messages.success(request, f'강의 "{title}"이(가) 성공적으로 생성되었습니다.')
        return redirect(
            "admin_portal_lecture_management",
            course_id=course.id,
            subject_id=subject.id,
        )

    # 현재 강의 수 가져오기 (기본 순서 인덱스 설정용)
    current_lecture_count = Lecture.objects.filter(subject=subject).count()

    context = {
        "course": course,
        "subject": subject,
        "next_order_index": current_lecture_count + 1,
    }

    return render(
        request, "admin_portal/course_management/lecture_create.html", context
    )


@login_required
def lecture_detail(request, course_id, subject_id, lecture_id):
    """강의 상세 및 수정 페이지"""
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    course = get_object_or_404(Course, id=course_id)
    subject = get_object_or_404(Subject, id=subject_id, course=course)
    lecture = get_object_or_404(Lecture, id=lecture_id, subject=subject)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "update":
            # 강의 업데이트
            lecture.title = request.POST.get("title")
            lecture.description = request.POST.get("description")
            lecture.order_index = request.POST.get("order_index")

            # 동영상 강의인 경우 비디오 파일 처리
            if lecture.lecture_type == "video" and "video_file" in request.FILES:
                lecture.video_file = request.FILES["video_file"]

            lecture.save()

            # 미션(퀴즈) 강의인 경우 문제 업데이트
            if lecture.lecture_type == "quiz" and "questions" in request.POST:
                # 기존 문제 삭제
                MissionQuestion.objects.filter(lecture=lecture).delete()

                # 새 문제 추가
                questions_data = json.loads(request.POST.get("questions"))

                for q_data in questions_data:
                    question = MissionQuestion(
                        lecture=lecture,
                        text=q_data["text"],
                        option1=q_data["options"][0],
                        option2=q_data["options"][1],
                        option3=q_data["options"][2],
                        option4=q_data["options"][3],
                        option5=q_data["options"][4],
                        correct_answer=q_data["correct_answer"],
                    )
                    question.save()

            messages.success(
                request, f'강의 "{lecture.title}"이(가) 성공적으로 업데이트되었습니다.'
            )

        elif action == "delete":
            # 강의 삭제
            title = lecture.title
            lecture.delete()
            messages.success(
                request, f'강의 "{title}"이(가) 성공적으로 삭제되었습니다.'
            )
            return redirect(
                "admin_portal_lecture_management",
                course_id=course.id,
                subject_id=subject.id,
            )

        return redirect(
            "admin_portal_lecture_management",
            course_id=course.id,
            subject_id=subject.id,
        )

    # 퀴즈 강의인 경우 문제 목록 가져오기
    questions = []
    if lecture.lecture_type == "quiz":
        questions = MissionQuestion.objects.filter(lecture=lecture)

    context = {
        "course": course,
        "subject": subject,
        "lecture": lecture,
        "questions": questions,
    }

    return render(
        request, "admin_portal/course_management/lecture_detail.html", context
    )


@login_required
def user_learning_records(request):
    """사용자 학습 기록 페이지"""
    # 관리자만 접근 가능하도록 체크
    if not request.user.is_admin:
        return redirect("learning_dashboard")  # 일반 사용자 대시보드로 리디렉션

    # 모든 학생 사용자 목록 (관리자 제외)
    all_users = User.objects.filter(is_admin=False).order_by("username")

    # 필터링 옵션
    selected_user_id = request.GET.get("user_id")
    selected_date_str = request.GET.get("date")

    # 날짜 필터링 (기본값: 오늘)
    today = timezone.now().date()

    try:
        selected_date = (
            date.fromisoformat(selected_date_str) if selected_date_str else today
        )
    except ValueError:
        selected_date = today

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

    # 페이지네이션 적용
    paginator = Paginator(daily_activities_query, 20)  # 페이지당 20개 항목
    page = request.GET.get("page")

    try:
        daily_activities = paginator.page(page)
    except PageNotAnInteger:
        # 페이지가 정수가 아니면 첫 페이지
        daily_activities = paginator.page(1)
    except EmptyPage:
        # 페이지가 범위를 벗어나면 마지막 페이지
        daily_activities = paginator.page(paginator.num_pages)

    context = {
        "all_users": all_users,
        "selected_user": selected_user,
        "selected_user_id": (
            int(selected_user_id)
            if selected_user_id and selected_user_id.isdigit()
            else None
        ),
        "selected_date": selected_date,
        "daily_activities": daily_activities,
        "enrollments": enrollments,
        "enrolled_courses_count": enrolled_courses_count,
        "completed_courses_count": completed_courses_count,
        "avg_progress": avg_progress,
    }

    return render(request, "admin_portal/user_learning_records.html", context)
