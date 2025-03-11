from django.core.files import File
from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion
from pathlib import Path
import random


User = get_user_model()


class Command(BaseCommand):
    help = "샘플 과정 데이터를 생성합니다."

    def handle(self, *args, **options):
        self.stdout.write("샘플 과정 데이터 생성 시작...")

        # 관리자 계정이 없으면 생성
        if not User.objects.filter(is_admin=True).exists():
            admin_user = User.objects.create_user(
                username="admin",
                email="admin@example.com",
                password="admin123",
                is_admin=True,
                is_staff=True,
                is_superuser=True,
            )
            self.stdout.write(
                self.style.SUCCESS(f"관리자 계정 생성: {admin_user.username}")
            )
        else:
            admin_user = User.objects.filter(is_admin=True).first()
            self.stdout.write(f"기존 관리자 계정 사용: {admin_user.username}")

        # InstructorProfile 생성 또는 가져오기
        instructor_profile, created = InstructorProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                "bio": "10년 경력의 웹 개발 강사입니다.",
                "experience": "다양한 기업에서 웹 개발 교육을 진행했습니다.",
                "qualification": "컴퓨터 공학 박사",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"강사 프로필 생성: {instructor_profile}")
            )
        else:
            self.stdout.write(f"기존 강사 프로필 사용: {instructor_profile}")

        # 샘플 과정 생성
        courses_data = [
            {
                "title": "웹 개발 기초 마스터",
                "description": "웹 개발의 기초부터, HTML, CSS, JavaScript까지 탄탄하게 배우는 과정입니다.",
                "short_description": "웹 개발의 핵심 기술을 한번에!",
                "difficulty_level": "beginner",
                "target_audience": "웹 개발을 처음 시작하는 분들을 위한 과정입니다.",
                "estimated_time": 30,  # 30시간
                "credit": 3,
                "price": 49900.00,
            },
            {
                "title": "파이썬 백엔드 개발 과정",
                "description": "파이썬과 Django를 활용한 백엔드 개발의 모든 것을 배우는 심화 과정입니다.",
                "short_description": "파이썬으로 백엔드 개발 역량 키우기",
                "difficulty_level": "intermediate",
                "target_audience": "Python 기초 지식이 있는 개발자, 백엔드 개발에 관심 있는 분들",
                "estimated_time": 40,  # 40시간
                "credit": 4,
                "price": 69900.00,
            },
        ]

        created_courses = []

        for course_data in courses_data:
            course, created = Course.objects.get_or_create(
                title=course_data["title"],
                defaults={
                    **course_data,
                    "instructor": instructor_profile,
                },
            )

            created_courses.append(course)

            if created:
                self.stdout.write(self.style.SUCCESS(f"과정 생성: {course.title}"))
            else:
                self.stdout.write(f"기존 과정 사용: {course.title}")
                # 기존 과정의 과목과 강의 삭제
                course.subjects.all().delete()

        # 샘플 과목 및 강의 생성
        for course in created_courses:
            if course.title == "웹 개발 기초 마스터":
                subjects_data = [
                    {
                        "title": "HTML 기초",
                        "description": "HTML의 기본 구조와 주요 태그 학습",
                        "order_index": 1,
                        "subject_type": "normal",
                    },
                    {
                        "title": "CSS 스타일링",
                        "description": "CSS를 활용한 웹 페이지 스타일링",
                        "order_index": 2,
                        "subject_type": "normal",
                    },
                    {
                        "title": "JavaScript 기초",
                        "description": "JavaScript 기본 문법과 DOM 조작",
                        "order_index": 3,
                        "subject_type": "normal",
                    },
                    {
                        "title": "중간 프로젝트",
                        "description": "지금까지 배운 내용을 활용한 중간 프로젝트",
                        "order_index": 4,
                        "subject_type": "midterm",
                    },
                    {
                        "title": "반응형 웹 디자인",
                        "description": "다양한 화면 크기에 대응하는 반응형 웹 디자인",
                        "order_index": 5,
                        "subject_type": "normal",
                    },
                    {
                        "title": "웹 접근성과 SEO",
                        "description": "웹 접근성과 검색 엔진 최적화",
                        "order_index": 6,
                        "subject_type": "normal",
                    },
                    {
                        "title": "최종 프로젝트",
                        "description": "포트폴리오용 최종 프로젝트",
                        "order_index": 7,
                        "subject_type": "final",
                    },
                ]
            else:  # 파이썬 백엔드 개발 과정
                subjects_data = [
                    {
                        "title": "Python 심화",
                        "description": "Python 고급 기능과 최적화",
                        "order_index": 1,
                        "subject_type": "normal",
                    },
                    {
                        "title": "Django 기초",
                        "description": "Django 프레임워크 기본 구조와 MVT 패턴",
                        "order_index": 2,
                        "subject_type": "normal",
                    },
                    {
                        "title": "Django 모델과 ORM",
                        "description": "Django 모델 설계와 ORM 활용",
                        "order_index": 3,
                        "subject_type": "normal",
                    },
                    {
                        "title": "중간 프로젝트",
                        "description": "Django를 활용한 간단한 웹 애플리케이션 개발",
                        "order_index": 4,
                        "subject_type": "midterm",
                    },
                    {
                        "title": "REST API 개발",
                        "description": "Django Rest Framework를 활용한 API 개발",
                        "order_index": 5,
                        "subject_type": "normal",
                    },
                    {
                        "title": "인증과 권한 관리",
                        "description": "사용자 인증과 권한 관리 시스템 구현",
                        "order_index": 6,
                        "subject_type": "normal",
                    },
                    {
                        "title": "최종 프로젝트",
                        "description": "완전한 백엔드 시스템 구현 프로젝트",
                        "order_index": 7,
                        "subject_type": "final",
                    },
                ]

            for subject_data in subjects_data:
                subject = Subject.objects.create(course=course, **subject_data)
                self.stdout.write(
                    f"과목 생성: {subject.title} (타입: {subject.subject_type})"
                )

                # 일반 과목인 경우 강의 생성
                if subject.subject_type == "normal":
                    lectures_data = []

                    # 예시 강의 데이터 생성
                    for i in range(1, 5):  # 4개의 동영상 강의
                        lectures_data.append(
                            {
                                "title": f"{subject.title} - 강의 {i}",
                                "description": f"{subject.title}의 {i}번째 강의입니다.",
                                "order_index": i,
                                "lecture_type": "video",
                                "duration": random.randint(10, 60),  # 10분~60분
                            }
                        )

                    # 마지막에 미션 강의 추가
                    lectures_data.append(
                        {
                            "title": f"{subject.title} - 미션",
                            "description": f"{subject.title} 과목의 미션 테스트입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                        }
                    )

                    for lecture_data in lectures_data:
                        lecture = Lecture.objects.create(
                            subject=subject, **lecture_data
                        )
                        self.stdout.write(
                            f"강의 생성: {lecture.title} (타입: {lecture.lecture_type})"
                        )

                        # 미션 강의인 경우 문제 생성
                        if lecture.lecture_type == "mission":
                            for q_index in range(1, 6):  # 5개의 문제
                                question = MissionQuestion.objects.create(
                                    lecture=lecture,
                                    question_text=f"{subject.title}에 관한 {q_index}번 문제입니다. 다음 중 올바른 것은?",
                                    option1="첫 번째 선택지",
                                    option2="두 번째 선택지",
                                    option3="세 번째 선택지 (정답)",
                                    option4="네 번째 선택지",
                                    option5="다섯 번째 선택지",
                                    correct_answer=3,  # 3번째가 정답
                                    order_index=q_index,
                                )
                                self.stdout.write(
                                    f"문제 생성: {question.question_text[:30]}..."
                                )

                        else:  # "video"
                            if Path("media/videos/sample.mp4").exists():
                                with open("media/videos/sample.mp4", "rb") as f:
                                    lecture.video_url.save(
                                        "sample.mp4", File(f), save=True
                                    )

        self.stdout.write(self.style.SUCCESS("샘플 과정 데이터 생성 완료!"))
