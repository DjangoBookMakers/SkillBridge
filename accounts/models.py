from django.db import models
from django.contrib.auth.models import AbstractUser


class User(AbstractUser):
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
