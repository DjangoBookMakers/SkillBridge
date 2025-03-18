from django.db.models.signals import post_save
from django.dispatch import receiver
import logging

from .models import LectureProgress, MissionAttempt, ProjectSubmission, Enrollment

logger = logging.getLogger("django")


@receiver(post_save, sender=LectureProgress)
@receiver(post_save, sender=MissionAttempt)
@receiver(post_save, sender=ProjectSubmission)
def update_enrollment_status(sender, instance, created=False, **kwargs):
    """수강 진행 상태 변경 시 Enrollment 상태를 자동으로 업데이트하는 시그널 핸들러"""
    try:
        # 모델 유형에 따라 사용자와 과정 정보 가져오기
        if sender == LectureProgress:
            user = instance.user
            course = instance.lecture.subject.course
            item_type = "lecture"
        elif sender == MissionAttempt:
            # 미션이 통과된 경우에만 상태 체크
            if not instance.is_passed:
                return
            user = instance.user
            course = instance.lecture.subject.course
            item_type = "mission"
        elif sender == ProjectSubmission:
            # 프로젝트가 통과된 경우에만 상태 체크
            if not instance.is_passed:
                return
            user = instance.user
            course = instance.subject.course
            item_type = "project"

        # 수강 정보 가져오기
        enrollment = Enrollment.objects.get(user=user, course=course)

        # 이전 상태 기록
        previous_status = enrollment.status

        # 완료 여부 체크 및 상태 업데이트
        enrollment.check_completion()

        # 상태 변경 로깅
        if previous_status != enrollment.status:
            logger.info(
                f"Enrollment status updated: user={user.username}, course={course.title}, "
                f"from={previous_status}, to={enrollment.status}, triggered_by={item_type}"
            )

    except Enrollment.DoesNotExist:
        logger.warning(
            f"Enrollment not found for user_id={instance.user.id}, triggered_by={sender.__name__}"
        )
    except Exception as e:
        logger.error(
            f"Error updating enrollment status: {str(e)}, triggered_by={sender.__name__}"
        )
