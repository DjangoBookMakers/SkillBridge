from django.db import models
from accounts.models import User, InstructorProfile


class Course(models.Model):
    """과정(나노디그리) 모델"""

    DIFFICULTY_CHOICES = [
        ("beginner", "입문"),
        ("basic", "초급"),
        ("intermediate", "중급"),
        ("advanced", "고급"),
    ]

    title = models.CharField(max_length=50)
    description = models.TextField()
    short_description = models.CharField(max_length=200, blank=True)
    thumbnail_image = models.ImageField(
        upload_to="courses/thumbnails/", null=True, blank=True
    )
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES)
    target_audience = models.TextField(blank=True)
    estimated_time = models.IntegerField(help_text="예상 학습시간(시간)")
    credit = models.IntegerField(help_text="학점")
    price = models.DecimalField(
        max_digits=10, decimal_places=0, help_text="원 단위 가격"
    )
    instructor = models.ForeignKey(
        InstructorProfile, on_delete=models.CASCADE, related_name="courses"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    # TODO: 과정의 평균 평점 계산
    # def average_rating(self):
    #     """과정의 평균 평점 계산"""
    #     reviews = self.reviews.all()
    #     if not reviews:
    #         return 0
    #     return sum(review.rating for review in reviews) / len(reviews)

    # TODO:
    # estimated_time을 @property로 변환


class Subject(models.Model):
    """과목 모델"""

    SUBJECT_TYPE_CHOICES = [
        ("normal", "일반"),
        ("midterm", "중간고사"),
        ("final", "기말고사"),
    ]

    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="subjects"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order_index = models.IntegerField(help_text="과목 순서")
    subject_type = models.CharField(
        max_length=20, choices=SUBJECT_TYPE_CHOICES, default="normal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.title} - {self.title}"


class Lecture(models.Model):
    """강의 모델"""

    LECTURE_TYPE_CHOICES = [
        ("video", "동영상"),
        ("mission", "미션"),
    ]

    subject = models.ForeignKey(
        Subject, on_delete=models.CASCADE, related_name="lectures"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    order_index = models.IntegerField(help_text="강의 순서")
    lecture_type = models.CharField(max_length=20, choices=LECTURE_TYPE_CHOICES)
    video_url = models.FileField(upload_to="videos/", null=True, blank=True)
    duration = models.IntegerField(help_text="동영상 길이(초)", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["order_index"]

    def __str__(self):
        return f"{self.subject.title} - {self.title}"


class MissionQuestion(models.Model):
    """미션 문제(쪽지시험) 모델"""

    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="questions"
    )
    question_text = models.TextField()
    option1 = models.TextField()
    option2 = models.TextField()
    option3 = models.TextField()
    option4 = models.TextField()
    option5 = models.TextField()
    correct_answer = models.IntegerField(help_text="1~5 정답 번호")
    order_index = models.IntegerField(help_text="문제 순서")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"문제: {self.question_text[:50]}..."


class QnAQuestion(models.Model):
    """Q&A 질문 모델"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="questions")
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, related_name="questions"
    )
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"질문: {self.content[:50]}..."


class QnAAnswer(models.Model):
    """Q&A 답변 모델"""

    question = models.ForeignKey(
        QnAQuestion, on_delete=models.CASCADE, related_name="answers"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="answers")
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"답변: {self.content[:50]}..."


class CourseReview(models.Model):
    """과정 리뷰 모델"""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="reviews")
    rating = models.IntegerField(help_text="리뷰 평점 1-5")
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [
            "user",
            "course",
        ]  # 한 사용자는 하나의 과정에 하나의 리뷰만 작성 가능

    def __str__(self):
        return f"{self.user.username}의 {self.course.title} 리뷰"
