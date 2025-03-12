from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg
from datetime import timedelta
import json

from accounts.models import User
from courses.models import Course
from learning.models import Enrollment, Certificate, ProjectSubmission
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

    # 차트 데이터 JSON 형식으로 변환
    chart_data = {
        "dates": dates,
        "new_users": new_users_data,
        "active_users": active_users_data,
        "new_enrollments": new_enrollments_data,
    }

    context = {
        "total_students": total_students,
        "total_courses": total_courses,
        "total_enrollments": total_enrollments,
        "total_certificates": total_certificates,
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
