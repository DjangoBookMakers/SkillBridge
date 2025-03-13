from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncWeek
from datetime import timedelta, date
import json
import io
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER

from accounts.models import User
from courses.models import Course, Subject, Lecture
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
    """특정 과정의 출석부 PDF 생성"""
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

    # 요청된 기간 처리
    selected_period = request.GET.get("period", "")

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

    # PDF 생성
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        alignment=TA_CENTER,
        fontSize=16,
        spaceAfter=12,
    )

    # 표 데이터 생성
    data = [
        # 헤더
        [
            "사용자 ID",
            "이름",
            *[day.strftime("%m/%d") for day in date_range],
            "전체 진행률(%)",
        ],
        # 데이터 행
        *attendance_data,
    ]

    # 표 스타일
    table_style = TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
            ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ("GRID", (0, 0), (-1, -1), 1, colors.black),
            ("ALIGN", (2, 1), (-2, -1), "CENTER"),  # 날짜 칼럼은 가운데 정렬
            ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),  # 진행률 칼럼은 오른쪽 정렬
        ]
    )

    table = Table(data)
    table.setStyle(table_style)

    # 문서 요소
    elements = [
        Paragraph(f"{course.title} - 수강생 출석부", title_style),
        Paragraph(
            f"기간: {start_date.strftime('%Y-%m-%d')} ~ {end_date.strftime('%Y-%m-%d')}",
            styles["Normal"],
        ),
        Spacer(1, 0.2 * inch),
        table,
    ]

    # PDF 생성
    doc.build(elements)

    # PDF 파일 응답
    buffer.seek(0)
    response = HttpResponse(buffer, content_type="application/pdf")
    filename = f'attendance_{course.title}_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.pdf'
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    return response
