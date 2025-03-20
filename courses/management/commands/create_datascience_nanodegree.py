from django.core.management import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from pathlib import Path
from django.core.files import File

from accounts.models import InstructorProfile
from courses.models import Course, Subject, Lecture, MissionQuestion

User = get_user_model()


class Command(BaseCommand):
    help = "데이터 사이언스 나노디그리 과정 데이터를 생성합니다."

    def handle(self, *args, **options):
        self.stdout.write("데이터 사이언스 나노디그리 과정 데이터 생성 시작...")

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
                "bio": "12년 경력의 데이터 사이언스 전문가입니다.",
                "experience": "삼성전자, 네이버에서 데이터 사이언티스트로 근무했으며, 현재는 대학에서 강의와 연구를 병행하고 있습니다.",
                "qualification": "통계학 박사, Google 인증 TensorFlow 개발자",
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
                title="데이터 사이언스 나노디그리",
                defaults={
                    "description": (
                        "데이터 사이언스의 기초부터 고급 기법까지 체계적으로 배우는 종합 과정입니다. "
                        "통계 분석, 머신러닝, 딥러닝, 데이터 시각화 등 데이터 사이언티스트에게 "
                        "필요한 모든 핵심 역량을 실무 프로젝트를 통해 습득합니다. "
                        "Python, Pandas, Scikit-learn, TensorFlow를 활용한 데이터 분석과 "
                        "모델링 능력을 기르고, 실제 기업 환경에서 발생하는 문제를 "
                        "데이터 기반으로 해결하는 방법론을 학습합니다."
                    ),
                    "short_description": "통계부터 머신러닝, 딥러닝까지 데이터 사이언스 완전 정복",
                    "difficulty_level": "basic",
                    "target_audience": "프로그래밍 기초 지식이 있는 초보자부터 데이터 분석 역량을 강화하려는 실무자까지",
                    "estimated_time": 90,  # 90시간
                    "credit": 9,
                    "price": 399000.00,
                    "instructor": instructor_profile,
                },
            )

            if created:
                self.stdout.write(self.style.SUCCESS(f"과정 생성: {course.title}"))

                # 썸네일 이미지 추가
                try:
                    # 샘플 이미지 파일 경로 - 실제 이미지 파일이 있는 경로로 수정하세요
                    sample_image_path = Path(
                        "media/thumbnails/datascience_thumbnail.jpg"
                    )

                    # 파일이 존재하는지 확인하고 없으면 기본 이미지 사용
                    if not sample_image_path.exists():
                        sample_image_path = Path(
                            "media/thumbnails/default_thumbnail.jpg"
                        )

                    if sample_image_path.exists():
                        with open(sample_image_path, "rb") as f:
                            course.thumbnail_image.save(
                                "datascience_nanodegree.jpg", File(f), save=True
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
                    "title": "데이터 분석 기초",
                    "description": "데이터 분석의 기본 개념과 Python을 활용한 데이터 처리 기법을 학습합니다.",
                    "order_index": 1,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "데이터 사이언스 소개",
                            "description": "데이터 사이언스의 정의, 데이터 사이언티스트의 역할, 주요 응용 분야를 소개합니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "Python 데이터 분석 환경 설정",
                            "description": "Anaconda, Jupyter Notebook, 주요 라이브러리 설치 및 기본 환경 구성 방법을 배웁니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 40,
                        },
                        {
                            "title": "NumPy 기초",
                            "description": "NumPy 배열과 연산, 인덱싱/슬라이싱, 브로드캐스팅 등 과학 계산을 위한 기본 도구를 학습합니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "Pandas 기초",
                            "description": "Pandas DataFrame, Series, 데이터 선택/필터링, 결측치 처리 등 데이터 조작 방법을 배웁니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "데이터 분석 기초 미션",
                            "description": "Python을 활용한 데이터 분석 기초 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 Pandas의 주요 데이터 구조가 아닌 것은?",
                                    "option1": "Series",
                                    "option2": "DataFrame",
                                    "option3": "Index",
                                    "option4": "Array",
                                    "option5": "Panel",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "NumPy에서 배열의 차원을 반환하는 속성은?",
                                    "option1": "array.dim",
                                    "option2": "array.ndim",
                                    "option3": "array.shape",
                                    "option4": "array.size",
                                    "option5": "array.dimensions",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "Pandas DataFrame에서 결측값을 찾는 메서드는?",
                                    "option1": "isna() 또는 isnull()",
                                    "option2": "findna()",
                                    "option3": "missing()",
                                    "option4": "hasnull()",
                                    "option5": "find_missing()",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "다음 중 Pandas에서 그룹별 연산을 수행하는 메서드는?",
                                    "option1": "group()",
                                    "option2": "segment()",
                                    "option3": "groupby()",
                                    "option4": "split()",
                                    "option5": "cluster()",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "Python에서 데이터 시각화를 위해 가장 널리 사용되는 라이브러리는?",
                                    "option1": "Seaborn",
                                    "option2": "Matplotlib",
                                    "option3": "Bokeh",
                                    "option4": "Plotly",
                                    "option5": "ggplot",
                                    "correct_answer": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "탐색적 데이터 분석(EDA)",
                    "description": "데이터의 특성을 파악하고 인사이트를 도출하는 다양한 분석 및 시각화 기법을 학습합니다.",
                    "order_index": 2,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "데이터 전처리 기법",
                            "description": "데이터 정제, 변환, 집계, 정규화 등 실무 데이터 전처리 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "데이터 시각화 기초",
                            "description": "Matplotlib과 Seaborn을 활용한 다양한 그래프 작성 및 시각화 기법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "통계적 데이터 분석",
                            "description": "기술 통계, 확률 분포, 가설 검정 등 통계적 데이터 분석 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "고급 시각화 및 대시보드",
                            "description": "Plotly, Dash를 활용한 인터랙티브 시각화와 대시보드 구축 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "탐색적 데이터 분석 미션",
                            "description": "EDA 기법과 시각화 지식을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "상관 분석에서 피어슨 상관계수의 범위는?",
                                    "option1": "0부터 1까지",
                                    "option2": "0부터 100까지",
                                    "option3": "-1부터 1까지",
                                    "option4": "-100부터 100까지",
                                    "option5": "제한 없음",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "범주형 변수의 분포를 시각화하기에 가장 적합한 그래프는?",
                                    "option1": "히스토그램",
                                    "option2": "산점도",
                                    "option3": "박스 플롯",
                                    "option4": "막대 그래프",
                                    "option5": "라인 차트",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "이상치(Outlier) 탐지에 가장 적합한 시각화 방법은?",
                                    "option1": "히스토그램",
                                    "option2": "박스 플롯",
                                    "option3": "막대 그래프",
                                    "option4": "원형 차트",
                                    "option5": "스택 플롯",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "두 변수 간의 관계를 시각화하는 데 적합한 그래프는?",
                                    "option1": "히스토그램",
                                    "option2": "산점도",
                                    "option3": "파이 차트",
                                    "option4": "막대 그래프",
                                    "option5": "지도",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "시계열 데이터 시각화에 가장 적합한 그래프는?",
                                    "option1": "라인 차트",
                                    "option2": "막대 그래프",
                                    "option3": "파이 차트",
                                    "option4": "산점도",
                                    "option5": "히트맵",
                                    "correct_answer": 1,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "데이터 분석 중간 프로젝트",
                    "description": "지금까지 배운 데이터 분석과 시각화 기법을 활용한 탐색적 데이터 분석 프로젝트입니다.",
                    "order_index": 3,
                    "subject_type": "midterm",
                },
                {
                    "title": "머신러닝 기초",
                    "description": "지도 학습과 비지도 학습의 주요 알고리즘과 활용 방법을 학습합니다.",
                    "order_index": 4,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "머신러닝 개요",
                            "description": "머신러닝의 기본 개념, 유형, 학습 과정 및 주요 응용 분야를 소개합니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "지도 학습: 회귀",
                            "description": "선형 회귀, 다항 회귀, 릿지/라쏘 회귀 등 회귀 알고리즘의 이론과 구현 방법을 배웁니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "지도 학습: 분류",
                            "description": "로지스틱 회귀, 의사결정트리, 랜덤 포레스트, SVM 등 분류 알고리즘의 원리와 활용법을 학습합니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 65,
                        },
                        {
                            "title": "비지도 학습: 군집화와 차원 축소",
                            "description": "K-평균 군집화, 계층적 군집화, PCA, t-SNE 등 비지도 학습 기법의 원리와 구현 방법을 배웁니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "머신러닝 기초 미션",
                            "description": "머신러닝 기초 알고리즘의 이해도를 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 지도 학습(Supervised Learning) 알고리즘이 아닌 것은?",
                                    "option1": "선형 회귀",
                                    "option2": "로지스틱 회귀",
                                    "option3": "랜덤 포레스트",
                                    "option4": "K-평균 군집화",
                                    "option5": "서포트 벡터 머신",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "과적합(Overfitting)을 방지하기 위한 방법이 아닌 것은?",
                                    "option1": "교차 검증",
                                    "option2": "규제화(Regularization)",
                                    "option3": "특성 추가",
                                    "option4": "앙상블 기법",
                                    "option5": "드롭아웃",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "분류 모델의 성능 평가 지표가 아닌 것은?",
                                    "option1": "정확도(Accuracy)",
                                    "option2": "정밀도(Precision)",
                                    "option3": "재현율(Recall)",
                                    "option4": "F1 점수",
                                    "option5": "평균 제곱 오차(MSE)",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "의사결정트리 알고리즘에서 노드 분할 기준으로 사용되는 것은?",
                                    "option1": "평균 제곱 오차",
                                    "option2": "정보 이득 또는 지니 불순도",
                                    "option3": "유클리디안 거리",
                                    "option4": "코사인 유사도",
                                    "option5": "L1/L2 규제",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "다음 중 차원 축소 알고리즘은?",
                                    "option1": "AdaBoost",
                                    "option2": "나이브 베이즈",
                                    "option3": "K-최근접 이웃(KNN)",
                                    "option4": "주성분 분석(PCA)",
                                    "option5": "XGBoost",
                                    "correct_answer": 4,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "머신러닝 심화",
                    "description": "모델 평가, 하이퍼파라미터 튜닝, 앙상블 기법 등 머신러닝 모델 개발의 심화 과정을 학습합니다.",
                    "order_index": 5,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "모델 평가 및 검증",
                            "description": "교차 검증, 성능 지표, ROC 곡선, 오차 행렬 등 모델 평가 방법론을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "하이퍼파라미터 튜닝",
                            "description": "그리드 서치, 랜덤 서치, 베이지안 최적화 등 하이퍼파라미터 튜닝 기법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "앙상블 학습",
                            "description": "배깅, 부스팅, 스태킹 등 앙상블 학습 기법과 XGBoost, LightGBM 등 고급 앙상블 알고리즘을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "특성 공학과 선택",
                            "description": "효과적인 특성 추출, 변환, 선택 및 중요도 평가 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "머신러닝 심화 미션",
                            "description": "머신러닝 심화 개념과 실무 적용 능력을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 배깅(Bagging) 기법을 사용하는 알고리즘은?",
                                    "option1": "AdaBoost",
                                    "option2": "랜덤 포레스트",
                                    "option3": "그래디언트 부스팅",
                                    "option4": "XGBoost",
                                    "option5": "LightGBM",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "k-겹 교차 검증(k-fold cross-validation)에서 k=5일 때 훈련/검증 데이터 비율은?",
                                    "option1": "50% / 50%",
                                    "option2": "80% / 20%",
                                    "option3": "90% / 10%",
                                    "option4": "95% / 5%",
                                    "option5": "99% / 1%",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "하이퍼파라미터 최적화 방법 중 가장 계산 효율적인 것은?",
                                    "option1": "무작위 검색",
                                    "option2": "그리드 검색",
                                    "option3": "베이지안 최적화",
                                    "option4": "유전 알고리즘",
                                    "option5": "완전 탐색",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "분류 불균형 문제에 대처하는 방법이 아닌 것은?",
                                    "option1": "오버샘플링",
                                    "option2": "언더샘플링",
                                    "option3": "SMOTE",
                                    "option4": "비용 가중치 조정",
                                    "option5": "L2 정규화",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "다음 중 특성 선택 방법이 아닌 것은?",
                                    "option1": "상관계수 기반 선택",
                                    "option2": "정보 이득(Information Gain) 기반 선택",
                                    "option3": "주성분 분석(PCA) 기반 선택",
                                    "option4": "후진 소거법(Backward Elimination)",
                                    "option5": "ReLU 활성화 기반 선택",
                                    "correct_answer": 5,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "딥러닝과 신경망",
                    "description": "인공 신경망의 기본 원리와 TensorFlow/Keras를 활용한 딥러닝 모델 구현 방법을 학습합니다.",
                    "order_index": 6,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "신경망 기초와 퍼셉트론",
                            "description": "인공 신경망의 기본 구조, 퍼셉트론, 활성화 함수, 역전파 알고리즘 등 딥러닝의 기초 개념을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "TensorFlow와 Keras 입문",
                            "description": "TensorFlow와 Keras 프레임워크의 기본 사용법과 신경망 모델 구현 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "합성곱 신경망(CNN)",
                            "description": "이미지 처리를 위한 CNN의 구조, 원리, 구현 방법 및 응용 사례를 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "순환 신경망(RNN)과 LSTM",
                            "description": "시퀀스 데이터 처리를 위한 RNN, LSTM, GRU의 원리와 자연어 처리 응용 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 65,
                        },
                        {
                            "title": "딥러닝 미션",
                            "description": "딥러닝의 기본 개념과 구현 능력을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "딥러닝에서 흔히 사용되는 활성화 함수가 아닌 것은?",
                                    "option1": "ReLU",
                                    "option2": "Sigmoid",
                                    "option3": "Tanh",
                                    "option4": "Softmax",
                                    "option5": "PCA",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "CNN에서 특징 추출을 담당하는 주요 연산은?",
                                    "option1": "풀링(Pooling)",
                                    "option2": "배치 정규화",
                                    "option3": "드롭아웃",
                                    "option4": "합성곱(Convolution)",
                                    "option5": "역전파",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "장기 의존성 문제(Long-term dependency problem)를 해결하기 위해 설계된 모델은?",
                                    "option1": "CNN",
                                    "option2": "LSTM",
                                    "option3": "ANN",
                                    "option4": "GAN",
                                    "option5": "AutoEncoder",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "딥러닝 모델 훈련 시 과적합을 방지하는 기법이 아닌 것은?",
                                    "option1": "드롭아웃(Dropout)",
                                    "option2": "L1/L2 정규화",
                                    "option3": "조기 종료(Early Stopping)",
                                    "option4": "배치 정규화(Batch Normalization)",
                                    "option5": "배치 크기 증가(Increasing Batch Size)",
                                    "correct_answer": 5,
                                },
                                {
                                    "question_text": "Keras에서 sequential API를 사용해 딥러닝 모델을 구축할 때 레이어 추가에 사용하는 메서드는?",
                                    "option1": "add()",
                                    "option2": "append()",
                                    "option3": "insert()",
                                    "option4": "push()",
                                    "option5": "extend()",
                                    "correct_answer": 1,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "데이터 사이언스 실무 응용",
                    "description": "실제 비즈니스 문제에 데이터 사이언스 기법을 적용하는 방법과 모델 배포 과정을 학습합니다.",
                    "order_index": 7,
                    "subject_type": "normal",
                    "lectures": [
                        {
                            "title": "추천 시스템",
                            "description": "협업 필터링, 콘텐츠 기반 필터링, 하이브리드 접근 방식 등 추천 시스템의 원리와 구현 방법을 배웁니다.",
                            "order_index": 1,
                            "lecture_type": "video",
                            "duration": 55,
                        },
                        {
                            "title": "자연어 처리(NLP) 기초",
                            "description": "텍스트 전처리, 워드 임베딩, 감성 분석 등 자연어 처리의 기본 개념과 응용 방법을 학습합니다.",
                            "order_index": 2,
                            "lecture_type": "video",
                            "duration": 60,
                        },
                        {
                            "title": "시계열 데이터 분석",
                            "description": "ARIMA, Prophet, RNN 등을 활용한 시계열 데이터 분석 및 예측 방법을 배웁니다.",
                            "order_index": 3,
                            "lecture_type": "video",
                            "duration": 50,
                        },
                        {
                            "title": "모델 배포와 MLOps 기초",
                            "description": "Flask, Docker, 클라우드 서비스를 활용한 머신러닝 모델 배포 및 운영 방법을 학습합니다.",
                            "order_index": 4,
                            "lecture_type": "video",
                            "duration": 45,
                        },
                        {
                            "title": "데이터 사이언스 응용 미션",
                            "description": "데이터 사이언스 실무 응용 능력을 평가하는 미션입니다.",
                            "order_index": 5,
                            "lecture_type": "mission",
                            "questions": [
                                {
                                    "question_text": "다음 중 협업 필터링(Collaborative Filtering)에 기반한 추천 시스템에 대한 설명으로 옳은 것은?",
                                    "option1": "아이템의 속성을 분석하여 유사한 아이템을 추천한다",
                                    "option2": "사용자의 과거 행동과 유사한 사용자들의 선호도를 기반으로 추천한다",
                                    "option3": "미리 정의된 규칙에 따라 추천한다",
                                    "option4": "인구통계학적 정보만을 사용한다",
                                    "option5": "이미지 인식 기술을 활용한다",
                                    "correct_answer": 2,
                                },
                                {
                                    "question_text": "자연어 처리에서 단어를 벡터로 표현하는 기법은?",
                                    "option1": "Word2Vec",
                                    "option2": "PageRank",
                                    "option3": "AdaBoost",
                                    "option4": "t-SNE",
                                    "option5": "K-means",
                                    "correct_answer": 1,
                                },
                                {
                                    "question_text": "시계열 데이터의 정상성(Stationarity)을 확인하는 테스트는?",
                                    "option1": "t-test",
                                    "option2": "chi-squared test",
                                    "option3": "Dickey-Fuller test",
                                    "option4": "KS test",
                                    "option5": "Mann-Whitney U test",
                                    "correct_answer": 3,
                                },
                                {
                                    "question_text": "머신러닝 모델을 REST API로 배포하는 데 적합한 Python 프레임워크는?",
                                    "option1": "NumPy",
                                    "option2": "Matplotlib",
                                    "option3": "Pandas",
                                    "option4": "Flask",
                                    "option5": "Seaborn",
                                    "correct_answer": 4,
                                },
                                {
                                    "question_text": "MLOps에서 모델 성능을 지속적으로 모니터링하는 이유는?",
                                    "option1": "법적 요구사항을 충족하기 위해",
                                    "option2": "데이터 드리프트로 인한 성능 저하를 감지하기 위해",
                                    "option3": "개발자의 작업 효율성을 높이기 위해",
                                    "option4": "모델 훈련 비용을 절감하기 위해",
                                    "option5": "사용자 인터페이스를 개선하기 위해",
                                    "correct_answer": 2,
                                },
                            ],
                        },
                    ],
                },
                {
                    "title": "데이터 사이언스 최종 프로젝트",
                    "description": "지금까지 배운 모든 기술을 활용하여 실제 비즈니스 문제를 해결하는 종합 프로젝트입니다.",
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
            self.style.SUCCESS("데이터 사이언스 나노디그리 과정 생성 완료!")
        )
