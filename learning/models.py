from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Course, Subject, Lecture, MissionQuestion


class Enrollment(models.Model):
    """수강 신청 및 진행 상황 모델"""

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
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="enrolled")
    progress_percentage = models.IntegerField(
        default=0, help_text="과정 전체 진행률(%)"
    )
    certificate_number = models.CharField(max_length=50, blank=True, null=True)
    certificate_issued_at = models.DateTimeField(blank=True, null=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        unique_together = ["user", "course"]

    def __str__(self):
        return f"{self.user.username}의 {self.course.title} 수강"

    def update_progress(self):
        """수강 진행률 업데이트"""
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
        """다음에 학습할 강의 찾기"""
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
        """과정 수료 조건 확인 (최적화 버전)"""
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
    """강의 진행 상태 모델"""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lecture_progresses",
    )
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="progresses"
    )
    is_completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(blank=True, null=True)
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
    """미션(쪽지시험) 시도 모델"""

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
        """점수 계산 및 통과 여부 판단"""
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
    """중간/기말고사 프로젝트 제출 모델"""

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
    is_passed = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(blank=True, null=True)
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
    """수료증 모델"""

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
    certificate_number = models.CharField(max_length=50, unique=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    pdf_file = models.FileField(
        upload_to=certificate_upload_path, blank=True, null=True
    )

    def __str__(self):
        return f"{self.user.username}의 {self.enrollment.course.title} 수료증"

    def generate_certificate_number(self):
        """고유한 수료증 번호 생성"""
        import uuid
        from datetime import datetime

        # 현재 날짜와 UUID를 조합하여 고유 번호 생성
        date_str = datetime.now().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4().hex)[:8].upper()

        self.certificate_number = f"SB-{date_str}-{unique_id}"
        return self.certificate_number

    def generate_pdf(self):
        """수료증 PDF 생성"""
        # TODO: PDF 생성 로직 구현
        # 실제 구현은 별도 서비스나 라이브러리 사용 필요
        pass
