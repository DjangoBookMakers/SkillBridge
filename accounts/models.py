from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
    """사용자 계정 모델

    Django의 기본 User 모델을 확장하여 추가 필드를 포함합니다.
    프로필 이미지, 전화번호, 생년월일, 성별 등의 추가 정보와
    관리자 여부, 로그인/로그아웃 시간을 기록합니다.
    """

    profile_image = models.ImageField(upload_to="profiles/", null=True, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, blank=True)
    is_admin = models.BooleanField(default=False, db_index=True)
    login_at = models.DateTimeField(null=True, blank=True, db_index=True)
    logout_at = models.DateTimeField(null=True, blank=True, db_index=True)

    def __str__(self):
        return self.username


class InstructorProfile(models.Model):
    """강사 프로필 모델

    강사로 등록된 사용자의 추가 정보를 저장합니다.
    강사 소개, 경력, 자격 등의 정보를 포함합니다.
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="instructor_profile"
    )
    bio = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    qualification = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"강사 프로필: {self.user.username}"


class DeletedUserData(models.Model):
    """탈퇴한 사용자의 데이터를 익명화하여 보관하는 모델"""

    original_user_id = models.IntegerField(help_text="원래 사용자의 ID", db_index=True)
    username = models.CharField(max_length=150, help_text="익명화된 사용자명")
    email = models.EmailField(blank=True, null=True, help_text="익명화된 이메일")
    deleted_at = models.DateTimeField(auto_now_add=True, db_index=True)

    def __str__(self):
        return f"삭제된 사용자 {self.username} (ID: {self.original_user_id})"
