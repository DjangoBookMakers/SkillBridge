from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from pathlib import Path
from django.core.files import File

from accounts.models import InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion

User = get_user_model()


class Command(BaseCommand):
    help = "프론트엔드 개발자 나노디그리 과정 데이터를 생성합니다."

    def handle(self, *args, **options):
        self.stdout.write("프론트엔드 개발자 나노디그리 과정 데이터 생성 시작...")

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
                "bio": "10년 경력의 프론트엔드 개발 강사입니다.",
                "experience": "네이버, 카카오에서 프론트엔드 개발자로 근무했으며, 현재는 프리랜서 개발자와 강사 활동을 병행하고 있습니다.",
                "qualification": "컴퓨터 공학 학사, 웹 개발 석사",
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
                title="프론트엔드 개발자 나노디그리",
                defaults={
                    "description": (
                        "프론트엔드 개발의 기초부터 심화까지 전반적인 내용을 다루는 종합 과정입니다. "
                        "HTML, CSS, JavaScript의 기본부터 시작해 React.js를 활용한 SPA 개발, "
                        "TypeScript, 상태 관리, 테스트 자동화까지 현업에서 필요한 모든 기술 스택을 "
                        "체계적으로 학습합니다. 각 과목별 미션과 프로젝트를 통해 실무 역량을 키울 수 있으며, "
                        "과정 수료 후에는 프론트엔드 개발자로 취업할 수 있는 포트폴리오를 갖추게 됩니다."
                    ),
                    "short_description": "프론트엔드 개발의 기초부터 심화까지, 실무에 필요한 모든 기술 학습",
                    "difficulty_level": "beginner",
                    "target_audience": "웹 개발에 관심이 있는 초보자부터 이미 기초 지식이 있는 개발자까지",
                    "estimated_time": 80,  # 80시간
                    "credit": 8,
                    "price": 349000.00,
                    "instructor": instructor_profile,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"과정 생성: {course.title}"))
                # 필요 시 썸네일 이미지도 추가 가능
                try:
                    # 샘플 이미지 파일 경로 - 실제 이미지 파일이 있는 경로로 수정하세요
                    sample_image_path = Path("media/thumbnails/frontend_thumbnail.jpg")

                    # 파일이 존재하는지 확인하고 없으면 기본 이미지 사용
                    if not sample_image_path.exists():
                        sample_image_path = Path(
                            "media/thumbnails/default_thumbnail.jpg"
                        )

                    if sample_image_path.exists():
                        with open(sample_image_path, "rb") as f:
                            course.thumbnail_image.save(
                                "frontend_nanodegree.jpg", File(f), save=True
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
                    "title": "웹 개발 기초",
                    "description": "HTML, CSS, JavaScript의 기초를 배우고 웹 페이지 구조와 스타일링을 학습합니다.",
                    "order_index": 1,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "HTML 기초",
                            "description": "HTML 문서 구조, 태그, 시맨틱 마크업 등 웹 개발의 기초를 학습합니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "CSS 스타일링",
                            "description": "CSS 선택자, 박스 모델, 레이아웃, 반응형 디자인의 기본 개념을 배웁니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "JavaScript 기초",
                            "description": "변수, 함수, 조건문, 반복문 등 JavaScript의 기본 문법을 학습합니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "DOM 조작",
                            "description": "Document Object Model의 개념과 JavaScript를 사용한 DOM 조작 방법을 배웁니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "웹 개발 기초 미션",
                            "description": "HTML, CSS, JavaScript의 기초 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 HTML5의 시맨틱 태그가 아닌 것은?",
                                    "option1": "<header>",
                                    "option2": "<section>",
                                    "option3": "<div>",
                                    "option4": "<article>",
                                    "option5": "<footer>",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "CSS에서 '!important'의 역할은 무엇인가요?",
                                    "option1": "특정 속성을 최우선으로 적용한다",
                                    "option2": "브라우저 호환성을 보장한다",
                                    "option3": "성능을 최적화한다",
                                    "option4": "코드의 가독성을 높인다",
                                    "option5": "스타일 적용을 무시한다",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "JavaScript에서 변수를 선언하는 키워드가 아닌 것은?",
                                    "option1": "var",
                                    "option2": "let",
                                    "option3": "const",
                                    "option4": "function",
                                    "option5": "static",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "다음 중 DOM 조작을 위한 JavaScript 메서드가 아닌 것은?",
                                    "option1": "getElementById()",
                                    "option2": "querySelector()",
                                    "option3": "createHTMLElement()",
                                    "option4": "appendChild()",
                                    "option5": "addEventListener()",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "반응형 웹 디자인을 구현하기 위해 필요한 CSS 속성은?",
                                    "option1": "color",
                                    "option2": "font-size",
                                    "option3": "border",
                                    "option4": "media query",
                                    "option5": "animation",
                                    "correct_answer": 4,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "CSS 프레임워크와 모던 JavaScript",
                    "description": "CSS 프레임워크와 모던 JavaScript의 개념 및 활용법을 배웁니다.",
                    "order_index": 2,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "CSS 프레임워크 - Bootstrap",
                            "description": "Bootstrap을 활용한 반응형 웹 디자인 구현 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "CSS 프레임워크 - Tailwind CSS",
                            "description": "Tailwind CSS의 유틸리티 기반 접근 방식과 사용법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "ES6+ 문법",
                            "description": "화살표 함수, 템플릿 리터럴, 구조 분해, 스프레드 연산자 등 모던 JavaScript 문법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "비동기 처리와 Promise",
                            "description": "JavaScript의 비동기 프로그래밍과 Promise, async/await 사용법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "프레임워크와 모던 JavaScript 미션",
                            "description": "CSS 프레임워크와 모던 JavaScript 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "Bootstrap에서 그리드 시스템의 기본 컨테이너 클래스는?",
                                    "option1": ".grid",
                                    "option2": ".container",
                                    "option3": ".row",
                                    "option4": ".column",
                                    "option5": ".flex",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "Tailwind CSS의 주요 특징으로 올바른 것은?",
                                    "option1": "컴포넌트 기반 설계",
                                    "option2": "SASS 전처리기 필요",
                                    "option3": "유틸리티 우선 접근 방식",
                                    "option4": "jQuery 의존성",
                                    "option5": "CSS 변수 사용 불가",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "ES6에서 도입된 기능이 아닌 것은?",
                                    "option1": "let과 const",
                                    "option2": "화살표 함수",
                                    "option3": "템플릿 리터럴",
                                    "option4": "async/await",
                                    "option5": "구조 분해 할당",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "Promise의 상태가 아닌 것은?",
                                    "option1": "pending",
                                    "option2": "fulfilled",
                                    "option3": "rejected",
                                    "option4": "cancelled",
                                    "option5": "settled",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "다음 중 올바른 async/await 사용법은?",
                                    "option1": "async function() { await getData(); }",
                                    "option2": "function async() { await getData(); }",
                                    "option3": "function() { async await getData(); }",
                                    "option4": "await function() { getData(); }",
                                    "option5": "function() { getData() await; }",
                                    "correct_answer": 1,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "프론트엔드 중간 프로젝트",
                    "description": "지금까지 배운 웹 개발 기초와 CSS 프레임워크, 모던 JavaScript 지식을 활용한 프로젝트입니다.",
                    "order_index": 3,
                    "subject_type": "midterm",
                },
                {
                    "title": "React.js 기초",
                    "description": "React.js의 기본 개념과 컴포넌트 기반 개발 방법론을 학습합니다.",
                    "order_index": 4,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "React 소개 및 환경 설정",
                            "description": "React의 개념, Virtual DOM, 개발 환경 설정 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 40,
                        },
                        {
                            "title": "컴포넌트와 JSX",
                            "description": "React 컴포넌트의 개념과 JSX 문법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "상태(State)와 Props",
                            "description": "React의 상태 관리와 Props를 통한 컴포넌트 간 데이터 전달 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "이벤트 처리와 폼",
                            "description": "React에서의 이벤트 처리 방법과 폼 컴포넌트 활용법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "React.js 기초 미션",
                            "description": "React.js의 기본 개념과 활용법을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "React에서 상태(state)를 초기화하는 올바른 방법은?",
                                    "option1": "this.state = { count: 0 }",
                                    "option2": "const [count, setCount] = useState(0)",
                                    "option3": "state = { count: 0 }",
                                    "option4": "this.setState({ count: 0 })",
                                    "option5": "React.createState({ count: 0 })",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "React 컴포넌트의 생명주기 메서드가 아닌 것은?",
                                    "option1": "componentDidMount",
                                    "option2": "componentWillUpdate",
                                    "option3": "componentDidUpdate",
                                    "option4": "componentWillUnmount",
                                    "option5": "componentDidRender",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "React에서 조건부 렌더링을 구현하는 방법으로 올바른 것은?",
                                    "option1": "if(condition) { <Component /> }",
                                    "option2": "{condition ? <Component /> : null}",
                                    "option3": "<Component if={condition} />",
                                    "option4": "condition && <Component />",
                                    "option5": "<If condition={condition}><Component /></If>",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "React 훅(Hook)에 대한 설명으로 올바른 것은?",
                                    "option1": "클래스형 컴포넌트에서만 사용할 수 있다",
                                    "option2": "조건문 안에서 호출할 수 있다",
                                    "option3": "함수형 컴포넌트에 상태 관리 기능을 추가한다",
                                    "option4": "컴포넌트의 렌더링 성능을 저하시킨다",
                                    "option5": "React 16 이전 버전부터 사용 가능했다",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "React에서 이벤트 핸들러를 올바르게 바인딩하는 방법은?",
                                    "option1": "<button onClick={this.handleClick()}>클릭</button>",
                                    "option2": "<button onClick={this.handleClick}>클릭</button>",
                                    "option3": "<button onClick={handleClick}>클릭</button>",
                                    "option4": "<button onClick={function() { this.handleClick(); }}>클릭</button>",
                                    "option5": "<button onClick='this.handleClick'>클릭</button>",
                                    "correct_answer": 3,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "React.js 심화",
                    "description": "React.js 심화 개념과 효율적인 상태 관리, 성능 최적화 방법을 학습합니다.",
                    "order_index": 5,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "React Hooks 심화",
                            "description": "useEffect, useMemo, useCallback 등 다양한 React Hooks의 활용법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "컨텍스트 API와 전역 상태 관리",
                            "description": "React Context API를 활용한 전역 상태 관리 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "라우팅과 SPA 구현",
                            "description": "React Router를 활용한 싱글 페이지 애플리케이션 구현 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "성능 최적화 기법",
                            "description": "React 애플리케이션의 성능을 최적화하는 다양한 기법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "React.js 심화 미션",
                            "description": "React.js의 심화 개념과 활용법을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "useEffect 훅의 두 번째 인자로 빈 배열([])을 전달하면 어떻게 동작하나요?",
                                    "option1": "컴포넌트가 마운트될 때만 실행된다",
                                    "option2": "렌더링마다 실행된다",
                                    "option3": "전혀 실행되지 않는다",
                                    "option4": "컴포넌트가 언마운트될 때만 실행된다",
                                    "option5": "비동기적으로 실행된다",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "React에서 메모이제이션을 위해 사용하는 훅이 아닌 것은?",
                                    "option1": "useMemo",
                                    "option2": "useCallback",
                                    "option3": "React.memo",
                                    "option4": "useRef",
                                    "option5": "PureComponent",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "React Router v6에서 라우트를 정의하는 올바른 방법은?",
                                    "option1": "<Route path='/home' component={Home} />",
                                    "option2": "<Route path='/home'><Home /></Route>",
                                    "option3": "<Route path='/home' render={() => <Home />} />",
                                    "option4": "<Route path='/home' element={<Home />} />",
                                    "option5": "<Route><path='/home' element={<Home />}</Route>",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "Context API의 주요 구성요소가 아닌 것은?",
                                    "option1": "createContext",
                                    "option2": "Provider",
                                    "option3": "Consumer",
                                    "option4": "useContext",
                                    "option5": "connectContext",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "React의 렌더링 성능을 최적화하는 방법으로 올바르지 않은 것은?",
                                    "option1": "React.memo 사용하기",
                                    "option2": "key 속성에 인덱스 사용하기",
                                    "option3": "불필요한 리렌더링 방지하기",
                                    "option4": "useCallback 사용하기",
                                    "option5": "코드 스플리팅 활용하기",
                                    "correct_answer": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "TypeScript와 상태 관리",
                    "description": "TypeScript의 기본 개념과 Redux, MobX 등 상태 관리 라이브러리 활용법을 학습합니다.",
                    "order_index": 6,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "TypeScript 기초",
                            "description": "TypeScript의 기본 문법, 타입 시스템, 인터페이스 등을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "React와 TypeScript",
                            "description": "React 프로젝트에 TypeScript를 적용하는 방법과 타입 지정 패턴을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "Redux로 상태 관리하기",
                            "description": "Redux를 활용한 전역 상태 관리 패턴과 미들웨어 활용법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "현대적 상태 관리 라이브러리",
                            "description": "MobX, Recoil, Zustand 등 다양한 상태 관리 라이브러리의 특징과 활용법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "TypeScript와 상태 관리 미션",
                            "description": "TypeScript와 상태 관리 라이브러리 활용법을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "TypeScript에서 함수의 반환 타입을 지정하는 올바른 방법은?",
                                    "option1": "function add(a: number, b: number) -> number { return a + b; }",
                                    "option2": "function add(a: number, b: number): number { return a + b; }",
                                    "option3": "function add(a: number, b: number) { return (a + b) as number; }",
                                    "option4": "function add<number>(a: number, b: number) { return a + b; }",
                                    "option5": "function add(a: number, b: number) { return number(a + b); }",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "React 컴포넌트에서 TypeScript로 props의 타입을 정의하는 방법으로 올바른 것은?",
                                    "option1": "function Component(props: {name: string}) { ... }",
                                    "option2": "function Component(props) { props: {name: string} ... }",
                                    "option3": "function Component<{name: string}>(props) { ... }",
                                    "option4": "function Component(props: type {name: string}) { ... }",
                                    "option5": "function Component(props as {name: string}) { ... }",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "Redux의 핵심 개념이 아닌 것은?",
                                    "option1": "액션(Action)",
                                    "option2": "리듀서(Reducer)",
                                    "option3": "스토어(Store)",
                                    "option4": "디스패치(Dispatch)",
                                    "option5": "컨트롤러(Controller)",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "Redux 미들웨어의 주요 용도로 올바른 것은?",
                                    "option1": "컴포넌트의 렌더링 최적화",
                                    "option2": "비동기 작업 처리",
                                    "option3": "DOM 직접 조작",
                                    "option4": "라우팅 관리",
                                    "option5": "CSS 스타일 동적 적용",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "다음 중 상태 관리 라이브러리가 아닌 것은?",
                                    "option1": "Redux",
                                    "option2": "MobX",
                                    "option3": "Recoil",
                                    "option4": "Zustand",
                                    "option5": "Formik",
                                    "correct_answer": 5,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "테스트와 배포",
                    "description": "프론트엔드 애플리케이션 테스트 방법론과 CI/CD를 활용한 배포 자동화 방법을 학습합니다.",
                    "order_index": 7,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "단위 테스트와 통합 테스트",
                            "description": "Jest와 React Testing Library를 활용한 단위 테스트와 통합 테스트 작성법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "E2E 테스트",
                            "description": "Cypress를 활용한 End-to-End 테스트 작성 및 자동화 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "CI/CD 파이프라인 구축",
                            "description": "GitHub Actions를 활용한 CI/CD 파이프라인 구축과 자동화 테스트 및 배포 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "클라우드 서비스에 배포하기",
                            "description": "Netlify, Vercel 등 클라우드 서비스를 활용한 프론트엔드 애플리케이션 배포 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 40,
                        },
                        {
                            "title": "테스트와 배포 미션",
                            "description": "프론트엔드 테스트 및 배포 자동화 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "Jest에서 비동기 코드를 테스트하는 올바른 방법은?",
                                    "option1": "test('async test', function() { asyncFunction(); });",
                                    "option2": "test('async test', async () => { await asyncFunction(); });",
                                    "option3": "test('async test', () => { return asyncFunction(); });",
                                    "option4": "test('async test', async function() { asyncFunction(); });",
                                    "option5": "test('async test', () => { asyncFunction().then(); });",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "React 컴포넌트 테스트에 적합한 도구는?",
                                    "option1": "Mocha",
                                    "option2": "Jasmine",
                                    "option3": "React Testing Library",
                                    "option4": "Chai",
                                    "option5": "Sinon",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "E2E 테스트 도구가 아닌 것은?",
                                    "option1": "Cypress",
                                    "option2": "Puppeteer",
                                    "option3": "Selenium",
                                    "option4": "TestCafe",
                                    "option5": "Enzyme",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "CI/CD의 의미로 올바른 것은?",
                                    "option1": "Continuous Improvement/Continuous Development",
                                    "option2": "Code Integration/Code Deployment",
                                    "option3": "Continuous Integration/Continuous Deployment",
                                    "option4": "Compiled Integration/Compiled Deployment",
                                    "option5": "Concurrent Integration/Concurrent Deployment",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "다음 중 정적 웹사이트 호스팅 서비스가 아닌 것은?",
                                    "option1": "Netlify",
                                    "option2": "GitHub Pages",
                                    "option3": "Vercel",
                                    "option4": "Firebase Hosting",
                                    "option5": "MongoDB Atlas",
                                    "correct_answer": 5,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "프론트엔드 최종 프로젝트",
                    "description": "지금까지 배운 모든 기술을 활용하여 완성도 높은 프론트엔드 애플리케이션을 개발하는 프로젝트입니다.",
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
            self.style.SUCCESS("프론트엔드 개발자 나노디그리 과정 생성 완료!")
        )
