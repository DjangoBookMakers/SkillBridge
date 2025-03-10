from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.db import transaction

from courses.models import Course, Lecture, Subject
from learning.models import Enrollment, LectureProgress, MissionAttempt, Certificate

User = get_user_model()


class Command(BaseCommand):
    help = "샘플 수강 데이터를 생성합니다."

    def add_arguments(self, parser):
        parser.add_argument(
            "--complete",
            action="store_true",
            help="사용자별 과정 진행 상태를 설정합니다.",
        )

    def handle(self, *args, **options):
        # 존재하는 과정 확인
        courses = Course.objects.all()
        if not courses.exists():
            self.stdout.write(
                self.style.ERROR(
                    "과정 데이터가 없습니다. 먼저 create_sample_course 커맨드를 실행해주세요."
                )
            )
            return

        if courses.count() < 2:
            self.stdout.write(
                self.style.ERROR(
                    "최소 2개의 과정이 필요합니다. 먼저 create_sample_course 커맨드를 실행해주세요."
                )
            )
            return

        self.stdout.write("샘플 수강 데이터 생성 시작...")

        # 첫 번째 사용자 생성
        user1, created = User.objects.get_or_create(
            username="student1",
            defaults={"email": "student1@example.com", "is_active": True},
        )

        if created:
            user1.set_password("student123")
            user1.save()
            self.stdout.write(
                self.style.SUCCESS(f"첫 번째 사용자 생성: {user1.username}")
            )
        else:
            self.stdout.write(f"기존 사용자 사용: {user1.username}")

        # 두 번째 사용자 생성
        user2, created = User.objects.get_or_create(
            username="student2",
            defaults={"email": "student2@example.com", "is_active": True},
        )

        if created:
            user2.set_password("student123")
            user2.save()
            self.stdout.write(
                self.style.SUCCESS(f"두 번째 사용자 생성: {user2.username}")
            )
        else:
            self.stdout.write(f"기존 사용자 사용: {user2.username}")

        # 첫 번째 과정과 두 번째 과정 가져오기
        course1 = courses[0]
        course2 = courses[1]

        with transaction.atomic():
            # 모든 사용자에 대해 기본 수강 신청 생성
            for user, username in [(user1, "student1"), (user2, "student2")]:
                for course in courses:
                    enrollment, created = Enrollment.objects.get_or_create(
                        user=user,
                        course=course,
                        defaults={
                            "progress_percentage": 0,
                            "enrolled_at": timezone.now(),
                        },
                    )

                    if created:
                        self.stdout.write(f"{username}: {course.title} 과정 수강 신청")
                    else:
                        self.stdout.write(
                            f"{username}: {course.title} 과정 이미 수강 중"
                        )

            # --complete 옵션이 주어진 경우에만 세부적인 진행 상태 설정
            if options["complete"]:
                self.stdout.write("상세 진행 상태 설정 중...")

                # 첫 번째 사용자: 첫 번째 과정 0%, 두 번째 과정 50%

                # 두 번째 과정 절반 진행
                enrollment1_2 = Enrollment.objects.get(user=user1, course=course2)
                lectures_course2 = Lecture.objects.filter(
                    subject__course=course2
                ).order_by("subject__order_index", "order_index")
                total_lectures_course2 = lectures_course2.count()
                lectures_to_complete = lectures_course2[: total_lectures_course2 // 2]

                progress_count = 0
                for lecture in lectures_to_complete:
                    lecture_progress, _ = LectureProgress.objects.get_or_create(
                        user=user1,
                        lecture=lecture,
                        defaults={
                            "is_completed": True,
                            "completed_at": timezone.now(),
                        },
                    )

                    if not lecture_progress.is_completed:
                        lecture_progress.is_completed = True
                        lecture_progress.completed_at = timezone.now()
                        lecture_progress.save()

                    progress_count += 1

                    # 미션 강의인 경우 통과한 시도 생성
                    if lecture.lecture_type == "mission":
                        mission_attempt, _ = MissionAttempt.objects.get_or_create(
                            user=user1,
                            lecture=lecture,
                            defaults={
                                "score": 90,
                                "is_passed": True,
                                "user_answers": {
                                    "1": "3",
                                    "2": "3",
                                    "3": "3",
                                    "4": "3",
                                    "5": "3",
                                },
                                "completed_at": timezone.now(),
                            },
                        )

                # 진행률 업데이트
                enrollment1_2.progress_percentage = int(
                    (progress_count / total_lectures_course2) * 100
                )
                enrollment1_2.save()
                self.stdout.write(
                    f"student1: {course2.title} 과정 부분 진행 ({enrollment1_2.progress_percentage}%)"
                )

                # 두 번째 사용자: 첫 번째 과정 한 과목 빼고 완료, 두 번째 과정 100% 완료 및 수료증

                # 첫 번째 과정: 마지막 과목 빼고 모두 완료
                enrollment2_1 = Enrollment.objects.get(user=user2, course=course1)
                subjects_course1 = Subject.objects.filter(course=course1).order_by(
                    "order_index"
                )

                if subjects_course1.count() > 0:
                    subjects_list = list(subjects_course1)
                    subjects_to_complete = subjects_list[:-1]  # 마지막 과목 제외

                    total_lectures = 0
                    completed_lectures = 0

                    for subject in subjects_course1:
                        lectures = Lecture.objects.filter(subject=subject).order_by(
                            "order_index"
                        )
                        total_lectures += lectures.count()

                        # 마지막 과목이 아닌 경우 모든 강의 완료
                        if subject in subjects_to_complete:
                            for lecture in lectures:
                                lecture_progress, _ = (
                                    LectureProgress.objects.get_or_create(
                                        user=user2,
                                        lecture=lecture,
                                        defaults={
                                            "is_completed": True,
                                            "completed_at": timezone.now(),
                                        },
                                    )
                                )

                                if not lecture_progress.is_completed:
                                    lecture_progress.is_completed = True
                                    lecture_progress.completed_at = timezone.now()
                                    lecture_progress.save()

                                completed_lectures += 1

                                # 미션 강의인 경우 통과한 시도 생성
                                if lecture.lecture_type == "mission":
                                    mission_attempt, _ = (
                                        MissionAttempt.objects.get_or_create(
                                            user=user2,
                                            lecture=lecture,
                                            defaults={
                                                "score": 95,
                                                "is_passed": True,
                                                "user_answers": {
                                                    "1": "3",
                                                    "2": "3",
                                                    "3": "3",
                                                    "4": "3",
                                                    "5": "3",
                                                },
                                                "completed_at": timezone.now(),
                                            },
                                        )
                                    )

                    # 진행률 업데이트
                    if total_lectures > 0:
                        enrollment2_1.progress_percentage = int(
                            (completed_lectures / total_lectures) * 100
                        )
                        enrollment2_1.save()

                    self.stdout.write(
                        f"student2: {course1.title} 과정 부분 진행 ({enrollment2_1.progress_percentage}%, 마지막 과목 제외)"
                    )

                # 두 번째 과정: 완전히 완료 및 수료증 발급
                enrollment2_2 = Enrollment.objects.get(user=user2, course=course2)

                # 모든 강의 완료 처리
                lectures_course2 = Lecture.objects.filter(
                    subject__course=course2
                ).order_by("subject__order_index", "order_index")

                for lecture in lectures_course2:
                    lecture_progress, _ = LectureProgress.objects.get_or_create(
                        user=user2,
                        lecture=lecture,
                        defaults={
                            "is_completed": True,
                            "completed_at": timezone.now(),
                        },
                    )

                    if not lecture_progress.is_completed:
                        lecture_progress.is_completed = True
                        lecture_progress.completed_at = timezone.now()
                        lecture_progress.save()

                    # 미션 강의인 경우 통과한 시도 생성
                    if lecture.lecture_type == "mission":
                        mission_attempt, _ = MissionAttempt.objects.get_or_create(
                            user=user2,
                            lecture=lecture,
                            defaults={
                                "score": 100,
                                "is_passed": True,
                                "user_answers": {
                                    "1": "3",
                                    "2": "3",
                                    "3": "3",
                                    "4": "3",
                                    "5": "3",
                                },
                                "completed_at": timezone.now(),
                            },
                        )

                # 진행률 100%로 설정
                enrollment2_2.progress_percentage = 100
                enrollment2_2.status = "completed"
                enrollment2_2.completed_at = timezone.now()
                enrollment2_2.save()

                # 수료증 생성
                certificate, created = Certificate.objects.get_or_create(
                    user=user2,
                    enrollment=enrollment2_2,
                    defaults={
                        "certificate_number": f"SAMPLE-{timezone.now().strftime('%Y%m%d')}-{user2.id}",
                        "issued_at": timezone.now(),
                    },
                )

                # 수강 상태 업데이트
                enrollment2_2.status = "certified"
                enrollment2_2.certificate_number = certificate.certificate_number
                enrollment2_2.certificate_issued_at = certificate.issued_at
                enrollment2_2.save()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"student2: {course2.title} 과정 완료 및 수료증 발급"
                    )
                )

        self.stdout.write(self.style.SUCCESS("샘플 수강 데이터 생성 완료!"))
        self.stdout.write("")

        # 사용자 정보 출력
        self.stdout.write("생성된 사용자 정보:")
        self.stdout.write(f"  사용자명: {user1.username} / 비밀번호: student123")
        self.stdout.write(f"  사용자명: {user2.username} / 비밀번호: student123")
        self.stdout.write("")

        if options["complete"]:
            self.stdout.write("진행 상태:")
            self.stdout.write("  student1: 첫 번째 과정 0%, 두 번째 과정 약 50%")
            self.stdout.write(
                "  student2: 첫 번째 과정 마지막 과목 제외 완료, 두 번째 과정 100% 완료 및 수료증 발급"
            )
        else:
            self.stdout.write(
                "모든 사용자의 모든 과정이 0% 진행 상태로 생성되었습니다."
            )
            self.stdout.write(
                "상세 진행 상태를 설정하려면 --complete 옵션을 사용하세요:"
            )
            self.stdout.write("  python manage.py create_sample_enrollment --complete")

        self.stdout.write("")
        self.stdout.write(
            "이제 생성된 사용자로 로그인하여 수강생 대시보드와 과정 학습 기능을 테스트할 수 있습니다."
        )
