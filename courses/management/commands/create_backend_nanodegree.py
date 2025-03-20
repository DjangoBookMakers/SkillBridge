from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from pathlib import Path
from django.core.files import File

from accounts.models import InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion

User = get_user_model()


class Command(BaseCommand):
    help = "백엔드 개발자 나노디그리 과정 데이터를 생성합니다."

    def handle(self, *args, **options):
        self.stdout.write("백엔드 개발자 나노디그리 과정 데이터 생성 시작...")

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
                "bio": "15년 경력의 백엔드 개발 전문가입니다.",
                "experience": "카카오, 라인에서 백엔드 개발자로 근무했으며, 현재는 AWS 인증 솔루션스 아키텍트로 활동하고 있습니다.",
                "qualification": "컴퓨터 공학 석사, AWS 공인 솔루션스 아키텍트 전문가",
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f"강사 프로필 생성: {instructor_profile}")
            )
        else:
            self.stdout.write(f"기존 강사 프로필 사용: {instructor_profile}")

        # 과정 생성
        with transaction.atomic():
            course, created = Course.objects.get_or_create(
                title="백엔드 개발자 나노디그리",
                defaults={
                    "description": (
                        "백엔드 개발의 핵심 기술과 실무 역량을 키우는 종합 과정입니다. "
                        "Python, Django, FastAPI를 활용한 API 개발부터 데이터베이스 설계, "
                        "서버 인프라 구축, 클라우드 배포, 보안 및 성능 최적화까지 "
                        "현업에서 요구하는 모든 백엔드 개발 스킬을 체계적으로 학습합니다. "
                        "각 단계별 실습과 프로젝트를 통해 실전 경험을 쌓고, "
                        "과정 수료 후에는 백엔드 개발자로 바로 활동할 수 있는 역량을 갖추게 됩니다."
                    ),
                    "short_description": "Python, Django, FastAPI를 활용한 백엔드 개발 실무 역량 완성",
                    "difficulty_level": "intermediate",
                    "target_audience": "프로그래밍 기초 지식이 있는 개발 입문자, 백엔드 개발로 전향하려는 개발자",
                    "estimated_time": 100,  # 100시간
                    "credit": 10,
                    "price": 429000.00,
                    "instructor": instructor_profile,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"과정 생성: {course.title}"))

                # 썸네일 이미지 추가
                try:
                    # 샘플 이미지 파일 경로 - 실제 이미지 파일이 있는 경로로 수정하세요
                    sample_image_path = Path("media/thumbnails/backend_thumbnail.jpg")

                    # 파일이 존재하는지 확인하고 없으면 기본 이미지 사용
                    if not sample_image_path.exists():
                        sample_image_path = Path(
                            "media/thumbnails/default_thumbnail.jpg"
                        )

                    if sample_image_path.exists():
                        with open(sample_image_path, "rb") as f:
                            course.thumbnail_image.save(
                                "backend_nanodegree.jpg", File(f), save=True
                            )
                        self.stdout.write(
                            self.style.SUCCESS("과정 썸네일 이미지 추가 완료")
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING("사용 가능한 썸네일 이미지가 없습니다")
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f"썸네일 이미지 설정 실패: {str(e)}")
                    )
            else:
                self.stdout.write(f"기존 과정 업데이트: {course.title}")
                # 기존 과정의 과목과 강의 삭제
                course.subjects.all().delete()

            # 과목 데이터 정의
            subjects_data = [
                {
                    "title": "Python 심화 프로그래밍",
                    "description": "백엔드 개발에 필요한 Python 심화 기능과 효율적인 코드 작성법을 학습합니다.",
                    "order_index": 1,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "함수형 프로그래밍과 일급 객체",
                            "description": "Python의 함수형 프로그래밍 패러다임과 일급 객체로서의 함수 활용법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "이터레이터와 제너레이터",
                            "description": "메모리 효율적인 프로그래밍을 위한 이터레이터와 제너레이터의 개념과 활용법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "데코레이터와 클로저",
                            "description": "Python의 데코레이터와 클로저를 활용한 코드 재사용 및 기능 확장 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "동시성과 비동기 프로그래밍",
                            "description": "threading, multiprocessing, asyncio를 활용한 동시성 및 비동기 프로그래밍 기법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "Python 심화 미션",
                            "description": "Python 심화 개념과 활용법을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "파이썬에서 클로저(Closure)의 정의로 가장 적절한 것은?",
                                    "option1": "메모리를 관리하는 가비지 컬렉션 메커니즘",
                                    "option2": "내부 함수가 외부 함수의 변수를 참조하는 함수",
                                    "option3": "객체지향 프로그래밍에서 클래스 상속 구조",
                                    "option4": "함수의 실행을 지연시키는 메커니즘",
                                    "option5": "비동기 함수의 콜백 처리 방식",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "파이썬에서 제너레이터(Generator)를 생성하는 방법은?",
                                    "option1": "@generator 데코레이터 사용",
                                    "option2": "함수 내부에서 return 대신 yield 키워드 사용",
                                    "option3": "generator() 함수 호출",
                                    "option4": "list comprehension 사용",
                                    "option5": "Iterator 클래스 상속",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "함수형 프로그래밍의 특징이 아닌 것은?",
                                    "option1": "순수 함수 사용",
                                    "option2": "상태 변이 최소화",
                                    "option3": "일급 객체로서의 함수",
                                    "option4": "객체 간 상속 관계 활용",
                                    "option5": "고차 함수 활용",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "asyncio 라이브러리의 주요 목적은?",
                                    "option1": "멀티스레딩 구현",
                                    "option2": "병렬 처리",
                                    "option3": "이벤트 루프 기반 비동기 처리",
                                    "option4": "웹 서버 구현",
                                    "option5": "분산 컴퓨팅",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "메모리 사용량을 줄이는 파이썬 테크닉으로 가장 효과적인 것은?",
                                    "option1": "리스트 대신 제너레이터 사용",
                                    "option2": "전역 변수 활용",
                                    "option3": "재귀 함수 사용",
                                    "option4": "클래스 상속 구조 깊게 설계",
                                    "option5": "lambda 함수 활용",
                                    "correct_answer": 1,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "관계형 데이터베이스 설계",
                    "description": "효율적인 데이터베이스 구조 설계와 SQL 최적화 방법을 학습합니다.",
                    "order_index": 2,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "데이터베이스 정규화",
                            "description": "정규화 원칙과 단계별 정규화 과정을 통한 효율적인 데이터베이스 설계 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "고급 SQL 쿼리 작성",
                            "description": "조인, 서브쿼리, 윈도우 함수 등 고급 SQL 쿼리 작성법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "인덱싱과 쿼리 최적화",
                            "description": "데이터베이스 인덱스 설계와 쿼리 실행 계획을 통한 성능 최적화 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "트랜잭션과 동시성 제어",
                            "description": "트랜잭션 속성(ACID)과 동시성 제어 메커니즘을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "데이터베이스 설계 미션",
                            "description": "관계형 데이터베이스 설계와 SQL 최적화 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 3차 정규화(3NF)의 정의로 가장 적절한 것은?",
                                    "option1": "모든 속성이 원자값을 가짐",
                                    "option2": "부분 함수적 종속성 제거",
                                    "option3": "이행적 함수적 종속성 제거",
                                    "option4": "다치 종속성 제거",
                                    "option5": "조인 종속성 제거",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "SQL에서 윈도우 함수의 주요 용도는?",
                                    "option1": "데이터 삽입 및 업데이트",
                                    "option2": "테이블 간 조인 수행",
                                    "option3": "행 집합에 대한 계산 수행 및 순위 지정",
                                    "option4": "데이터베이스 스키마 변경",
                                    "option5": "트랜잭션 관리",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "데이터베이스 인덱스에 대한 설명으로 옳지 않은 것은?",
                                    "option1": "조회 성능을 향상시킨다",
                                    "option2": "삽입/수정/삭제 작업의 오버헤드가 있다",
                                    "option3": "B-Tree, Hash 등 다양한 구조로 구현 가능하다",
                                    "option4": "모든 테이블 컬럼에 인덱스를 생성할수록 성능이 향상된다",
                                    "option5": "복합 인덱스는 여러 컬럼을 포함할 수 있다",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "트랜잭션의 ACID 속성 중 'I'가 나타내는 것은?",
                                    "option1": "Identity (식별성)",
                                    "option2": "Isolation (격리성)",
                                    "option3": "Integration (통합성)",
                                    "option4": "Invariance (불변성)",
                                    "option5": "Implementation (구현)",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "다음 중 데드락(Deadlock)을 방지하는 방법으로 적절하지 않은 것은?",
                                    "option1": "트랜잭션의 잠금 획득 순서 통일",
                                    "option2": "타임아웃 설정",
                                    "option3": "트랜잭션 격리 수준 높이기",
                                    "option4": "트랜잭션 크기를 작게 유지",
                                    "option5": "잠금 감지 및 해결 알고리즘 사용",
                                    "correct_answer": 3,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "백엔드 중간 프로젝트",
                    "description": "지금까지 배운 Python 심화 개념과 데이터베이스 설계 지식을 활용한 중간 프로젝트입니다.",
                    "order_index": 3,
                    "subject_type": "midterm",
                },
                {
                    "title": "Django 웹 개발",
                    "description": "Django 프레임워크를 활용한 웹 애플리케이션 개발의 핵심 기술을 학습합니다.",
                    "order_index": 4,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "Django 아키텍처와 MVT 패턴",
                            "description": "Django의 기본 아키텍처와 MVT(Model-View-Template) 패턴의 이해 및 애플리케이션 구조 설계 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "모델 설계와 ORM",
                            "description": "Django ORM을 활용한 데이터베이스 모델 설계 및 쿼리 최적화 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "클래스 기반 뷰와 폼 처리",
                            "description": "클래스 기반 뷰의 장점과 활용법, Django 폼을 통한 데이터 유효성 검사 및 처리 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "인증과 권한 관리",
                            "description": "Django의 내장 인증 시스템과 권한 관리 기능을 활용한 보안 구현 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "Django 웹 개발 미션",
                            "description": "Django 웹 개발 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "Django의 MVT 패턴에서 'T'는 무엇을 의미하는가?",
                                    "option1": "Test",
                                    "option2": "Type",
                                    "option3": "Template",
                                    "option4": "Transaction",
                                    "option5": "Task",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "Django ORM에서 다음 쿼리의 실행 결과는?<br>`User.objects.filter(age__gte=18).exclude(status='inactive')`",
                                    "option1": "18세 미만이거나 상태가 inactive인 모든 사용자",
                                    "option2": "18세 이상이고 상태가 inactive가 아닌 모든 사용자",
                                    "option3": "18세 이상이거나 상태가 inactive가 아닌 모든 사용자",
                                    "option4": "18세 미만이고 상태가 inactive인 모든 사용자",
                                    "option5": "18세 이상인 모든 사용자 중 첫 번째 사용자",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "Django에서 모델 간 다대다(Many-to-Many) 관계를 정의하는 필드는?",
                                    "option1": "OneToOneField",
                                    "option2": "ForeignKey",
                                    "option3": "ManyToManyField",
                                    "option4": "RelatedField",
                                    "option5": "MultipleField",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "Django 클래스 기반 뷰 중 폼 제출을 처리하는 데 가장 적합한 것은?",
                                    "option1": "TemplateView",
                                    "option2": "DetailView",
                                    "option3": "ListView",
                                    "option4": "FormView",
                                    "option5": "RedirectView",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "Django에서 사용자 인증을 처리하는 기본 사용자 모델 클래스는?",
                                    "option1": "UserModel",
                                    "option2": "User",
                                    "option3": "UserAuth",
                                    "option4": "Account",
                                    "option5": "AuthUser",
                                    "correct_answer": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "RESTful API 개발",
                    "description": "Django REST Framework와 FastAPI를 활용한 RESTful API 설계 및 구현 방법을 학습합니다.",
                    "order_index": 5,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "REST 아키텍처와 API 설계 원칙",
                            "description": "REST 아키텍처의 기본 원칙과 RESTful API 설계 모범 사례를 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "Django REST Framework 기초",
                            "description": "Django REST Framework를 활용한 API 개발 기초와 Serializer, ViewSet 활용법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "FastAPI 입문과 비동기 API",
                            "description": "FastAPI 프레임워크를 활용한 고성능 비동기 API 개발 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "API 보안과 인증",
                            "description": "토큰 기반 인증, OAuth, JWT를 활용한 API 보안 구현 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "RESTful API 개발 미션",
                            "description": "RESTful API 설계 및 구현 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 RESTful API 설계 원칙에 맞지 않는 것은?",
                                    "option1": "리소스는 URI로 표현한다",
                                    "option2": "HTTP 메서드를 사용하여 작업을 표현한다",
                                    "option3": "응답에 하이퍼링크를 포함한다",
                                    "option4": "URL에 동사를 사용한다",
                                    "option5": "상태 코드를 통해 결과를 표현한다",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "Django REST Framework에서 Serializer의 주요 역할은?",
                                    "option1": "데이터베이스 쿼리 최적화",
                                    "option2": "모델 데이터와 JSON/XML 데이터 간 변환",
                                    "option3": "API 라우팅 처리",
                                    "option4": "인증 및 권한 관리",
                                    "option5": "비동기 요청 처리",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "FastAPI의 주요 특징이 아닌 것은?",
                                    "option1": "자동 API 문서 생성",
                                    "option2": "Python 타입 힌트 활용",
                                    "option3": "비동기 처리 지원",
                                    "option4": "내장 ORM 제공",
                                    "option5": "데이터 검증",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "JWT(JSON Web Token)의 구조로 옳은 것은?",
                                    "option1": "헤더 + 페이로드",
                                    "option2": "헤더 + 페이로드 + 시그니처",
                                    "option3": "페이로드 + 시그니처",
                                    "option4": "헤더 + 바디 + 푸터",
                                    "option5": "시그니처 + 인증코드",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "HTTP 상태 코드 403의 의미는?",
                                    "option1": "요청 성공",
                                    "option2": "리소스 생성 성공",
                                    "option3": "리소스를 찾을 수 없음",
                                    "option4": "권한 없음",
                                    "option5": "서버 내부 오류",
                                    "correct_answer": 4,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "서버 인프라와 클라우드 배포",
                    "description": "Docker, Kubernetes, AWS를 활용한 서버 인프라 구축 및 배포 자동화 방법을 학습합니다.",
                    "order_index": 6,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "Docker 컨테이너화",
                            "description": "Docker를 활용한 애플리케이션 컨테이너화와 개발/운영 환경 일치화 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "Kubernetes 기초",
                            "description": "Kubernetes를 활용한 컨테이너 오케스트레이션과 스케일링 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "AWS 클라우드 서비스",
                            "description": "AWS EC2, S3, RDS 등 주요 서비스를 활용한 클라우드 인프라 구축 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "CI/CD 파이프라인 구축",
                            "description": "GitHub Actions, Jenkins를 활용한 CI/CD 파이프라인 구축과 자동화 배포 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "서버 인프라와 배포 미션",
                            "description": "서버 인프라 구축 및 클라우드 배포 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "Docker 컨테이너와 가상 머신의 차이점으로 가장 적절한 것은?",
                                    "option1": "컨테이너는 OS 커널을 공유하지만, 가상 머신은 독립적인 OS를 갖는다",
                                    "option2": "컨테이너는 윈도우 환경에서만 실행 가능하다",
                                    "option3": "가상 머신이 컨테이너보다 더 가볍고 빠르게 시작된다",
                                    "option4": "컨테이너는 하드웨어 가상화가 필요하다",
                                    "option5": "가상 머신은 마이크로서비스 구현에 더 적합하다",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "Kubernetes에서 Pod의 정의로 가장 적절한 것은?",
                                    "option1": "컨테이너 이미지를 저장하는 레지스트리",
                                    "option2": "하나 이상의 컨테이너 그룹으로 배포의 기본 단위",
                                    "option3": "여러 노드를 관리하는 컨트롤러",
                                    "option4": "서비스 검색을 위한 DNS 서버",
                                    "option5": "컨테이너 간 통신을 위한 네트워크 프록시",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "AWS의 RDS 서비스는 무엇을 제공하는가?",
                                    "option1": "컨테이너 오케스트레이션",
                                    "option2": "객체 스토리지",
                                    "option3": "관계형 데이터베이스",
                                    "option4": "CDN 서비스",
                                    "option5": "서버리스 함수",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "CI/CD에서 'CD'가 의미하는 것은?",
                                    "option1": "Continuous Development",
                                    "option2": "Code Distribution",
                                    "option3": "Continuous Deployment/Delivery",
                                    "option4": "Container Deployment",
                                    "option5": "Configuration Definition",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "Blue-Green 배포 전략의 주요 이점은?",
                                    "option1": "서비스 중단 없이 배포 가능",
                                    "option2": "리소스 사용량 감소",
                                    "option3": "테스트 과정 생략 가능",
                                    "option4": "데이터베이스 마이그레이션 자동화",
                                    "option5": "보안 취약점 자동 탐지",
                                    "correct_answer": 1,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "백엔드 성능 최적화와 보안",
                    "description": "백엔드 애플리케이션의 성능 최적화 기법과 보안 취약점 대응 방법을 학습합니다.",
                    "order_index": 7,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "데이터베이스 성능 최적화",
                            "description": "쿼리 최적화, 인덱싱, 캐싱을 통한 데이터베이스 성능 향상 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "코드 레벨 최적화",
                            "description": "프로파일링, 메모리 관리, 알고리즘 개선을 통한 코드 레벨 성능 최적화 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "웹 보안 취약점과 대응책",
                            "description": "OWASP Top 10 보안 취약점과 이에 대한 효과적인 대응 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "부하 테스트와 모니터링",
                            "description": "부하 테스트 도구와 모니터링 시스템을 활용한 성능 이슈 탐지 및 해결 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "성능 최적화와 보안 미션",
                            "description": "백엔드 성능 최적화와 보안 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 데이터베이스 성능 최적화 방법으로 적절하지 않은 것은?",
                                    "option1": "적절한 인덱스 생성",
                                    "option2": "쿼리 실행 계획 분석",
                                    "option3": "필요한 데이터만 선택적으로 조회",
                                    "option4": "모든 테이블에 외래 키 제약 조건 추가",
                                    "option5": "N+1 쿼리 문제 해결",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "Python에서 메모리 사용량을 분석하는 도구는?",
                                    "option1": "pytest",
                                    "option2": "black",
                                    "option3": "flake8",
                                    "option4": "memory_profiler",
                                    "option5": "venv",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "OWASP Top 10에 포함되는 보안 취약점이 아닌 것은?",
                                    "option1": "인젝션",
                                    "option2": "크로스 사이트 스크립팅(XSS)",
                                    "option3": "취약한 인증",
                                    "option4": "하드코딩된 비밀번호",
                                    "option5": "하드웨어 오버클로킹",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "부하 테스트 도구로 적절한 것은?",
                                    "option1": "Wireshark",
                                    "option2": "JMeter",
                                    "option3": "Postman",
                                    "option4": "Visual Studio Code",
                                    "option5": "Git",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "웹 애플리케이션에서 CSRF 공격을 방지하는 방법은?",
                                    "option1": "SSL/TLS 인증서 사용",
                                    "option2": "트랜잭션마다 고유한 토큰 사용",
                                    "option3": "사용자 패스워드 해싱",
                                    "option4": "데이터베이스 암호화",
                                    "option5": "강력한 방화벽 설정",
                                    "correct_answer": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "백엔드 최종 프로젝트",
                    "description": "지금까지 배운 모든 기술을 활용하여 완성도 높은 백엔드 시스템을 구축하는 최종 프로젝트입니다.",
                    "order_index": 8,
                    "subject_type": "final",
                },
            ]

            # 과목 및 강의 생성
            for subject_data in subjects_data:
                lectures_data = subject_data.pop("lectures", [])
                subject = Subject.objects.create(course=course, **subject_data)
                self.stdout.write(
                    f"과목 생성: {subject.title} (타입: {subject.subject_type})"
                )

                # 일반 과목인 경우 강의 생성
                if subject.subject_type == "normal":
                    for lecture_data in lectures_data:
                        questions_data = lecture_data.pop("questions", [])
                        lecture = Lecture.objects.create(
                            subject=subject, **lecture_data
                        )
                        self.stdout.write(
                            f"  강의 생성: {lecture.title} (타입: {lecture.lecture_type})"
                        )

                        # 미션 강의인 경우 문제 생성
                        if lecture.lecture_type == "mission" and questions_data:
                            for q_index, question_data in enumerate(questions_data, 1):
                                question = MissionQuestion.objects.create(
                                    lecture=lecture,
                                    order_index=q_index,
                                    **question_data,
                                )
                                self.stdout.write(
                                    f"    문제 생성: {question.question_text[:30]}..."
                                )

                        # 비디오 강의인 경우 샘플 비디오 설정 (있는 경우)
                        if lecture.lecture_type == "video":
                            try:
                                # 샘플 비디오 파일이 있으면 설정
                                sample_video_path = Path("media/videos/sample.mp4")
                                if sample_video_path.exists():
                                    with open(sample_video_path, "rb") as f:
                                        lecture.video_file.save(
                                            f"sample_{lecture.id}.mp4",
                                            File(f),
                                            save=True,
                                        )
                            except Exception as e:
                                # 비디오 파일 없어도 진행 (에러 로그만 출력)
                                self.stdout.write(
                                    self.style.WARNING(
                                        f"비디오 파일 설정 실패: {str(e)}"
                                    )
                                )

        self.stdout.write(
            self.style.SUCCESS("백엔드 개발자 나노디그리 과정 생성 완료!")
        )
