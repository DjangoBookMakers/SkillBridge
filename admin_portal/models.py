from django.db import models
from django.utils import timezone
from accounts.models import User
from learning.models import (
    Enrollment,
    LectureProgress,
    Certificate,
)
import decimal
import logging

logger = logging.getLogger("django")


class DailyStatistics(models.Model):
    """일별 통계 정보를 저장하는 모델"""

    date = models.DateField(unique=True)
    new_users = models.PositiveIntegerField(default=0, help_text="신규 가입자 수")
    active_users = models.PositiveIntegerField(default=0, help_text="활성 사용자 수")
    new_enrollments = models.PositiveIntegerField(
        default=0, help_text="신규 수강 신청 수"
    )
    completed_lectures = models.PositiveIntegerField(
        default=0, help_text="완료된 강의 수"
    )
    certificates_issued = models.PositiveIntegerField(
        default=0, help_text="발급된 수료증 수"
    )
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=0,
        default=decimal.Decimal(0),
        help_text="일일 매출액",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.date} 통계"

    class Meta:
        verbose_name = "일별 통계"
        verbose_name_plural = "일별 통계 목록"
        ordering = ["-date"]

    @classmethod
    def update_daily_statistics(cls):
        """오늘 날짜의 통계 업데이트"""
        today = timezone.now().date()
        stats, created = cls.objects.get_or_create(date=today)

        if created:
            logger.info(f"Created new daily statistics record for {today}")
        else:
            logger.info(f"Updating existing daily statistics for {today}")

        # 신규 가입자 수
        today_start = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.min.time())
        )
        today_end = timezone.make_aware(
            timezone.datetime.combine(today, timezone.datetime.max.time())
        )
        stats.new_users = User.objects.filter(
            date_joined__range=(today_start, today_end)
        ).count()

        # 활성 사용자 수 (오늘 로그인)
        stats.active_users = User.objects.filter(
            last_login__range=(today_start, today_end)
        ).count()

        # 신규 수강 신청 수
        stats.new_enrollments = Enrollment.objects.filter(
            enrolled_at__range=(today_start, today_end)
        ).count()

        # 완료된 강의 수
        stats.completed_lectures = LectureProgress.objects.filter(
            completed_at__range=(today_start, today_end), is_completed=True
        ).count()

        # 발급된 수료증 수
        stats.certificates_issued = Certificate.objects.filter(
            issued_at__range=(today_start, today_end)
        ).count()

        # 일일 매출액 (실제 결제 시스템에 맞게 수정 필요)
        # stats.revenue = Payment.objects.filter(created_at__range=(today_start, today_end), payment_status='completed').aggregate(Sum('amount'))['amount__sum'] or 0

        stats.save()
        return stats
