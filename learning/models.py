from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Course, Subject, Lecture, MissionQuestion


class Enrollment(models.Model):
    """수강 신청 및 진행 상황 모델

    사용자가 과정을 수강하는 상태와 진행 상황을 관리합니다.
    """

    STATUS_CHOICES = [
        ("enrolled", "수강 중"),
        ("completed", "수료 완료"),
        ("certified", "수료증 발급"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="enrollments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="enrollments"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="enrolled", db_index=True
    )
    progress_percentage = models.IntegerField(
        default=0, help_text="과정 전체 진행률(%)"
    )
    certificate_number = models.CharField(max_length=50, blank=True, null=True)
    certificate_issued_at = models.DateTimeField(blank=True, null=True)
    enrolled_at = models.DateTimeField(auto_now_add=True, db_index=True)
    last_activity_at = models.DateTimeField(auto_now=True, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user.username}의 {self.course.title} 수강"

    def update_progress(self):
        """수강 진행률 업데이트

        과정에 포함된 모든 강의 중 완료한 강의의 비율을 계산하여
        progress_percentage 필드를 업데이트합니다.
        """
        # 전체 강의 수
        total_lectures = Lecture.objects.filter(subject__course=self.course).count()
        if total_lectures == 0:
            return 0

        # 완료한 강의 수
        completed_lectures = LectureProgress.objects.filter(
            user=self.user, lecture__subject__course=self.course, is_completed=True
        ).count()

        # 진행률 계산 및 업데이트
        progress = int((completed_lectures / total_lectures) * 100)
        self.progress_percentage = progress
        self.save(update_fields=["progress_percentage"])

        return progress

    def get_next_lecture(self):
        """다음에 학습할 강의 찾기

        사용자가 아직 완료하지 않은 가장 처음 강의를 반환합니다.
        모든 강의를 완료한 경우 첫 번째 강의를 반환합니다(복습용).
        """
        # 현재 과정의 모든 과목을 순서대로 가져오기
        subjects = Subject.objects.filter(course=self.course).order_by("order_index")

        for subject in subjects:
            # 과목 내 모든 강의를 순서대로 가져오기
            lectures = Lecture.objects.filter(subject=subject).order_by("order_index")

            for lecture in lectures:
                # 아직 완료하지 않은 강의가 있으면 반환
                progress = LectureProgress.objects.filter(
                    user=self.user, lecture=lecture, is_completed=True
                ).exists()

                if not progress:
                    return lecture

        # 모든 강의를 완료했다면 첫 번째 강의 반환 (복습용)
        first_lecture = (
            Lecture.objects.filter(subject__course=self.course)
            .order_by("subject__order_index", "order_index")
            .first()
        )

        return first_lecture

    def get_next_learning_item(self):
        """
        다음에 수행해야 할 학습 항목을 반환합니다.

        반환 형식: (유형, 객체)
        유형은 'video_lecture', 'mission', 'project', 'completed' 중 하나입니다.
        """
        # 과정의 모든 과목을 순서대로 확인
        subjects = Subject.objects.filter(course=self.course).order_by("order_index")

        for subject in subjects:
            # 중간고사/기말고사 과목인 경우
            if subject.subject_type in ["midterm", "final"]:
                # 이미 통과한 프로젝트가 있는지 확인
                submission = ProjectSubmission.objects.filter(
                    user=self.user, subject=subject, is_passed=True
                ).first()

                # 아직 통과하지 않았다면 프로젝트 제출로 반환
                if not submission:
                    return ("project", subject)

            # 일반 과목인 경우 미완료된 강의 찾기
            lectures = Lecture.objects.filter(subject=subject).order_by("order_index")

            for lecture in lectures:
                # 강의 진행 상태 확인
                progress = LectureProgress.objects.filter(
                    user=self.user, lecture=lecture, is_completed=True
                ).exists()

                # 완료하지 않은 강의가 있으면 해당 강의 반환
                if not progress:
                    if lecture.lecture_type == "video":
                        return ("video_lecture", lecture)
                    elif lecture.lecture_type == "mission":
                        return ("mission", lecture)

        # 모든 항목을 완료한 경우
        return ("completed", self.course)

    def check_completion(self):
        """과정 수료 조건 확인 (최적화 버전)

        모든 강의와 미션, 중간/기말고사를 완료했는지 확인하고,
        조건 충족 시 상태를 'completed'로 업데이트합니다.
        """
        # 이미 완료된 과정이면 즉시 True 반환
        if self.status == "completed":
            return True

        # 수강 중인 과정의 모든 과목
        subjects = Subject.objects.filter(course=self.course)

        # 중간/기말고사 과목 통과 여부 확인
        exam_subjects = subjects.filter(subject_type__in=["midterm", "final"])
        for subject in exam_subjects:
            if not ProjectSubmission.objects.filter(
                user=self.user, subject=subject, is_passed=True
            ).exists():
                return False

        # (중간고사 또는 기말고사 아닌) 일반 과목의 모든 강의 완료 여부 확인
        # lecture_ids: 일반 과목의 모든 강의의 강의 id 목록
        normal_subjects = subjects.filter(subject_type="normal")
        lecture_ids = Lecture.objects.filter(subject__in=normal_subjects).values_list(
            "id", flat=True
        )

        # 사용자의 모든 진행 상황 한 번에 가져오기
        # completed_lectures: 일반 과목의 모든 강의 중 완료된 것들의 강의 id 목록
        completed_lectures = set(
            LectureProgress.objects.filter(
                user=self.user, lecture_id__in=lecture_ids, is_completed=True
            ).values_list("lecture_id", flat=True)
        )

        # 미션 통과 여부 확인
        # passed_missions: 일반 과목의 모든 강의 중 'mission' 타입인 것들의 MissionAttempt 중 통과한 것들의 강의 id 목록
        passed_missions = set(
            MissionAttempt.objects.filter(
                user=self.user,
                lecture__subject__in=normal_subjects,
                lecture__lecture_type="mission",
                is_passed=True,
            ).values_list("lecture_id", flat=True)
        )

        # 일반 과목의 모든 강의 정보를 한 번에 가져오기
        lectures = {l.id: l for l in Lecture.objects.filter(id__in=lecture_ids)}

        # 일반 과목의 모든 강의에 대해 진행 상황 확인
        for lecture_id in lecture_ids:
            lecture = lectures[lecture_id]  # 쿼리 없이 딕셔너리에서 가져옴
            if lecture.lecture_type == "mission":
                if lecture_id not in passed_missions:
                    return False
            else:
                if lecture_id not in completed_lectures:
                    return False

        # 모든 조건 충족 시 상태 업데이트
        self.status = "completed"
        self.completed_at = timezone.now()
        self.save(update_fields=["status", "completed_at"])
        return True


class LectureProgress(models.Model):
    """강의 진행 상태 모델

    특정 사용자의 특정 강의 진행 상태를 관리합니다.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lecture_progresses",
    )
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="progresses"
    )
    is_completed = models.BooleanField(default=False, db_index=True)
    completed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["user", "lecture"]

    def __str__(self):
        return f"{self.user.username}의 {self.lecture.title} 진행 상태"

    def mark_as_completed(self):
        """강의를 완료 상태로 표시 (동영상 시청 시작만으로도 완료 처리)"""
        if not self.is_completed:
            self.is_completed = True
            self.completed_at = timezone.now()
            self.save(update_fields=["is_completed", "completed_at"])

            # 수강 진행률 업데이트
            enrollment = Enrollment.objects.get(
                user=self.user, course=self.lecture.subject.course
            )
            enrollment.update_progress()


class MissionAttempt(models.Model):
    """미션(쪽지시험) 시도 모델

    미션 타입 강의에 대한 사용자의 응시 정보를 저장합니다.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="mission_attempts",
    )
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="attempts"
    )
    score = models.IntegerField(default=0)
    is_passed = models.BooleanField(default=False)
    user_answers = models.JSONField(help_text="JSON 형식으로 저장된 사용자 답변")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.user.username}의 {self.lecture.title} 시도"

    def calculate_score(self):
        """점수 계산 및 통과 여부 판단

        사용자 답변과 정답을 비교하여 점수를 계산하고,
        80% 이상 정답인 경우 통과 처리합니다.
        통과한 경우 해당 강의의 진행 상태도 완료로 표시합니다.
        """
        total_questions = MissionQuestion.objects.filter(lecture=self.lecture).count()
        if total_questions == 0:
            return 0

        correct_count = 0
        for question_id, answer in self.user_answers.items():
            try:
                question = MissionQuestion.objects.get(id=int(question_id))
                if int(answer) == question.correct_answer:
                    correct_count += 1
            except (MissionQuestion.DoesNotExist, ValueError):
                pass

        # 점수 계산 (백분율)
        score = int((correct_count / total_questions) * 100)
        self.score = score

        # 80% 이상이면 통과
        self.is_passed = score >= 80
        self.completed_at = timezone.now()
        self.save(update_fields=["score", "is_passed", "completed_at"])

        # 미션 강의 진행 상태 업데이트
        if self.is_passed:
            lecture_progress, _ = LectureProgress.objects.get_or_create(
                user=self.user, lecture=self.lecture
            )
            lecture_progress.mark_as_completed()

        return score


class ProjectSubmission(models.Model):
    """중간/기말고사 프로젝트 제출 모델

    중간고사나 기말고사 과목에 대한 프로젝트 제출 정보를 저장합니다.
    """

    def project_file_upload_path(self, filename):
        """중간/기말고사 제출 파일 저장 경로 설정"""
        subject_type = self.subject.subject_type
        username = self.user.username
        import datetime

        date_str = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        return f"projects/{subject_type}/{username}/{date_str}/{filename}"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="project_submissions",
    )
    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="submissions"
    )
    project_file = models.FileField(upload_to=project_file_upload_path)
    is_passed = models.BooleanField(default=False, db_index=True)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(blank=True, null=True, db_index=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviews",
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.user.username}의 {self.subject.title} 프로젝트"


class Certificate(models.Model):
    """수료증 모델

    과정 완료 후 발급되는 수료증 정보를 저장합니다.
    """

    def certificate_upload_path(self, filename):
        """수료증 파일 저장 경로 설정"""
        username = self.user.username
        return f"certificates/{username}/{filename}"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="certificates"
    )
    enrollment = models.OneToOneField(
        Enrollment, on_delete=models.CASCADE, related_name="certificate"
    )
    certificate_number = models.CharField(max_length=50, unique=True, db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True, db_index=True)
    pdf_file = models.FileField(
        upload_to=certificate_upload_path, blank=True, null=True
    )

    def __str__(self):
        return f"{self.user.username}의 {self.enrollment.course.title} 수료증"

    def generate_certificate_number(self):
        """고유한 수료증 번호 생성

        현재 날짜와 UUID를 조합하여 'SB-{date_str}-{unique_id}' 형식의
        고유 수료증 번호를 생성합니다.
        """
        import uuid
        from datetime import datetime

        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4().hex)[:8].upper()

        self.certificate_number = f"SB-{date_str}-{unique_id}"
        return self.certificate_number

    def generate_pdf(self):
        """수료증 PDF 생성 - 웹 버전과 동일한 디자인

        ReportLab을 사용하여 수료증 PDF 파일을 생성하고,
        파일 객체를 pdf_file 필드에 저장합니다.
        """
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Image,
            Table,
            TableStyle,
        )
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from io import BytesIO
        from django.contrib.staticfiles.finders import find as find_static_file
        from django.core.files.base import ContentFile

        # 폰트 등록 (한글 지원을 위해)
        font_path = find_static_file("fonts/NanumGothic.ttf")
        if font_path:
            pdfmetrics.registerFont(TTFont("NanumGothic", font_path))
            pdfmetrics.registerFont(
                TTFont(
                    "NanumGothicBold",
                    find_static_file("fonts/NanumGothicBold.ttf") or font_path,
                )
            )
            font_name = "NanumGothic"
            font_name_bold = "NanumGothicBold"
        else:
            # 폰트를 찾지 못하면 기본 폰트 사용
            font_name = "Helvetica"
            font_name_bold = "Helvetica-Bold"

        # 스타일 정의
        styles = getSampleStyleSheet()

        # 스타일 추가
        styles.add(
            ParagraphStyle(
                name="TitleKO",
                fontName=font_name_bold,
                fontSize=24,
                alignment=TA_CENTER,
                spaceAfter=5,
            )
        )

        styles.add(
            ParagraphStyle(
                name="SubtitleKO",
                fontName=font_name,
                fontSize=14,
                alignment=TA_CENTER,
                spaceAfter=20,
            )
        )

        styles.add(
            ParagraphStyle(
                name="BodyKO",
                fontName=font_name,
                fontSize=12,
                alignment=TA_CENTER,
                leading=18,
            )
        )

        styles.add(
            ParagraphStyle(
                name="NameKO",
                fontName=font_name_bold,
                fontSize=16,
                alignment=TA_CENTER,
                spaceBefore=15,
                spaceAfter=15,
            )
        )

        styles.add(
            ParagraphStyle(
                name="CourseKO",
                fontName=font_name_bold,
                fontSize=18,
                alignment=TA_CENTER,
                spaceAfter=5,
                textColor=colors.blue,
            )
        )

        styles.add(
            ParagraphStyle(
                name="CreditKO",
                fontName=font_name,
                fontSize=12,
                alignment=TA_CENTER,
            )
        )

        styles.add(
            ParagraphStyle(
                name="InfoLeftKO",
                fontName=font_name,
                fontSize=10,
                alignment=TA_LEFT,
            )
        )

        styles.add(
            ParagraphStyle(
                name="InfoRightKO",
                fontName=font_name,
                fontSize=10,
                alignment=TA_RIGHT,
            )
        )

        # PDF 생성
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            leftMargin=72,
            rightMargin=72,
            topMargin=72,
            bottomMargin=72,
        )

        # PDF에 들어갈 요소들
        elements = []

        # 타이틀 로고
        elements.append(Paragraph("스킬브릿지", styles["TitleKO"]))
        elements.append(Spacer(1, 20))

        # 수료증
        elements.append(Paragraph("수료증", styles["TitleKO"]))
        elements.append(Paragraph("Certificate of Completion", styles["SubtitleKO"]))
        elements.append(Spacer(1, 30))

        # 본문
        elements.append(
            Paragraph(
                "본 증서는 아래의 교육과정을 성공적으로 이수하였음을 증명합니다.",
                styles["BodyKO"],
            )
        )
        elements.append(Spacer(1, 40))

        # 수료자 이름
        user_name = self.user.get_full_name() or self.user.username
        elements.append(Paragraph(f"{user_name}", styles["NameKO"]))

        # 과정명
        course_title = self.enrollment.course.title
        elements.append(Paragraph(f"{course_title}", styles["CourseKO"]))

        # 학점
        course_credit = self.enrollment.course.credit
        elements.append(Paragraph(f"총 학점: {course_credit}학점", styles["CreditKO"]))
        elements.append(Spacer(1, 50))

        # 발급번호 및 발급일 (테이블로 배치)
        issue_date = self.issued_at.strftime("%Y년 %m월 %d일")

        data = [
            [
                Paragraph("발급 번호", styles["InfoLeftKO"]),
                Paragraph("발급일", styles["InfoRightKO"]),
            ],
            [
                Paragraph(f"{self.certificate_number}", styles["InfoLeftKO"]),
                Paragraph(f"{issue_date}", styles["InfoRightKO"]),
            ],
        ]

        t = Table(data, colWidths=[doc.width / 2.0, doc.width / 2.0])
        t.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )

        elements.append(t)
        elements.append(Spacer(1, 50))

        # 직인 이미지
        seal_path = find_static_file("images/seal.png")
        if seal_path:
            seal = Image(seal_path, width=100, height=100)
            seal.hAlign = "CENTER"
            elements.append(seal)
        else:
            # 직인 이미지가 없는 경우, 텍스트로 대체
            elements.append(Paragraph("(직인)", styles["BodyKO"]))

        elements.append(Spacer(1, 20))

        # 기관명
        elements.append(Paragraph("스킬브릿지", styles["BodyKO"]))
        elements.append(Paragraph("대표: 홍길동", styles["BodyKO"]))

        # 배경에 테두리 추가를 위한 후처리 함수
        def add_border(canvas, doc):
            canvas.saveState()
            canvas.setStrokeColor(colors.black)
            canvas.setLineWidth(1)
            canvas.rect(
                doc.leftMargin - 10,
                doc.bottomMargin - 10,
                doc.width + 20,
                doc.height + 20,
            )
            canvas.restoreState()

        # PDF 생성 (배경 테두리 추가)
        doc.build(elements, onFirstPage=add_border, onLaterPages=add_border)

        # PDF 파일 저장
        pdf_content = buffer.getvalue()
        buffer.close()

        # 파일명 생성 (타임스탬프 추가로 유니크하게)
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        pdf_filename = f"certificate_{self.certificate_number}_{timestamp}.pdf"

        # 모델의 pdf_file 필드에 저장
        self.pdf_file.save(pdf_filename, ContentFile(pdf_content), save=True)

        return self.pdf_file
