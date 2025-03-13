from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta
import json

from accounts.models import User
from courses.models import Course
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
def admin_pending_projects(request):
    """평가 대기 중인 프로젝트 목록 페이지"""
    # 관리자만 접근 가능
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    # 검색 및 필터링 파라미터 받기
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "pending")

    # 기본 쿼리셋 생성 (관련 모델 조인)
    projects = ProjectSubmission.objects.select_related(
        "user", "subject", "subject__course"
    )

    # 상태별 필터링
    if status_filter == "pending":
        projects = projects.filter(is_passed=False, reviewed_at__isnull=True)
    elif status_filter == "reviewed":
        projects = projects.filter(reviewed_at__isnull=False)
    elif status_filter == "passed":
        projects = projects.filter(is_passed=True)

    # 검색어 필터링
    if search_query:
        projects = projects.filter(
            Q(user__username__icontains=search_query) |
            Q(subject__title__icontains=search_query) |
            Q(subject__course__title__icontains=search_query)
        )

    # 최근 제출 순으로 정렬
    projects = projects.order_by("-submitted_at")

    # 페이지네이션
    paginator = Paginator(projects, 10)
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

    return render(request, "admin_portal/pending_projects.html", context)@login_required
def admin_pending_projects(request):
    """평가 대기 중인 프로젝트 목록 페이지"""
    # 관리자만 접근 가능
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    # 검색 및 필터링 파라미터 받기
    search_query = request.GET.get("search", "")
    status_filter = request.GET.get("status", "pending")

    # 기본 쿼리셋 생성 (관련 모델 조인)
    projects = ProjectSubmission.objects.select_related(
        "user", "subject", "subject__course"
    )

    # 상태별 필터링
    if status_filter == "pending":
        projects = projects.filter(is_passed=False, reviewed_at__isnull=True)
    elif status_filter == "reviewed":
        projects = projects.filter(reviewed_at__isnull=False)
    elif status_filter == "passed":
        projects = projects.filter(is_passed=True)

    # 검색어 필터링
    if search_query:
        projects = projects.filter(
            Q(user__username__icontains=search_query) |
            Q(subject__title__icontains=search_query) |
            Q(subject__course__title__icontains=search_query)
        )

    # 최근 제출 순으로 정렬
    projects = projects.order_by("-submitted_at")

    # 페이지네이션
    paginator = Paginator(projects, 10)
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
    # 관리자만 접근 가능
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    # 프로젝트 상세 정보 가져오기
    project = get_object_or_404(
        ProjectSubmission, 
        id=project_id
    )

    context = {
        "project": project,
        "subject": project.subject,
        "course": project.subject.course,
        # 추가로 필요한 컨텍스트 정보
        "submissions": project.submissions.all() if hasattr(project, 'submissions') else None
    }

    return render(request, "admin_portal/project_detail.html", context)

    @login_required
def evaluate_project(request, project_id):
    """프로젝트 평가 페이지"""
    # 관리자만 접근 가능
    if not request.user.is_admin:
        return redirect("learning_dashboard")

    # 프로젝트 가져오기
    project = get_object_or_404(ProjectSubmission, id=project_id)

    if request.method == "POST":
        # 평가 처리
        is_passed = request.POST.get("is_passed") == "true"
        feedback = request.POST.get("feedback", "")

        # 프로젝트 상태 업데이트
        project.is_passed = is_passed
        project.feedback = feedback
        project.reviewed_at = timezone.now()
        project.reviewed_by = request.user
        project.save()

        messages.success(request, "프로젝트 평가가 완료되었습니다.")

        # 학생이 프로젝트를 통과했을 때 추가 처리
        if is_passed:
            try:
                # 해당 과정의 등록 정보 확인
                enrollment = Enrollment.objects.get(
                    user=project.user, 
                    course=project.subject.course
                )

                # 과정 완료 여부 체크
                enrollment.check_completion()

                # 과정이 완료되었다면 메시지 추가
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
def admin_statistics_api(request):
    """대시보드 통계 데이터 API (AJAX 요청용)"""
    # 관리자만 접근 가능
    if not request.user.is_admin:
        return JsonResponse({"error": "권한이 없습니다."}, status=403)

    # 기간 파라미터 받기 (기본 30일)
    period = request.GET.get("period", "30")

    try:
        days = int(period)
        if days <= 0:
            raise ValueError
    except ValueError:
        return JsonResponse({"error": "유효하지 않은 기간입니다."}, status=400)

    # 기간에 따른 통계 데이터 조회
    today = timezone.now().date()
    start_date = today - timedelta(days=days)

    # 기간 내 통계 데이터 필터링
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