# Generated by Django 5.1.6 on 2025-03-22 10:08

import django.db.models.deletion
import learning.models
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("courses", "0004_alter_course_created_at_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Enrollment",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("enrolled", "수강 중"),
                            ("completed", "수료 완료"),
                            ("certified", "수료증 발급"),
                        ],
                        db_index=True,
                        default="enrolled",
                        max_length=20,
                    ),
                ),
                (
                    "progress_percentage",
                    models.IntegerField(default=0, help_text="과정 전체 진행률(%)"),
                ),
                (
                    "certificate_number",
                    models.CharField(blank=True, max_length=50, null=True),
                ),
                ("certificate_issued_at", models.DateTimeField(blank=True, null=True)),
                ("enrolled_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "last_activity_at",
                    models.DateTimeField(auto_now=True, db_index=True),
                ),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "course",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to="courses.course",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="enrollments",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "course")},
            },
        ),
        migrations.CreateModel(
            name="Certificate",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "certificate_number",
                    models.CharField(db_index=True, max_length=50, unique=True),
                ),
                ("issued_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                (
                    "pdf_file",
                    models.FileField(
                        blank=True,
                        null=True,
                        upload_to=learning.models.Certificate.certificate_upload_path,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificates",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "enrollment",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="certificate",
                        to="learning.enrollment",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="MissionAttempt",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("score", models.IntegerField(default=0)),
                ("is_passed", models.BooleanField(default=False)),
                (
                    "user_answers",
                    models.JSONField(help_text="JSON 형식으로 저장된 사용자 답변"),
                ),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mission_attempts",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "lecture",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="attempts",
                        to="courses.lecture",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mission_attempts",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-started_at"],
            },
        ),
        migrations.CreateModel(
            name="ProjectSubmission",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "project_file",
                    models.FileField(
                        upload_to=learning.models.ProjectSubmission.project_file_upload_path
                    ),
                ),
                ("is_passed", models.BooleanField(db_index=True, default=False)),
                ("feedback", models.TextField(blank=True)),
                (
                    "submitted_at",
                    models.DateTimeField(auto_now_add=True, db_index=True),
                ),
                (
                    "reviewed_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_submissions",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "subject",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="submissions",
                        to="courses.subject",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="project_submissions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-submitted_at"],
            },
        ),
        migrations.CreateModel(
            name="LectureProgress",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("is_completed", models.BooleanField(db_index=True, default=False)),
                (
                    "completed_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "enrollment",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecture_progresses",
                        to="learning.enrollment",
                    ),
                ),
                (
                    "lecture",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="progresses",
                        to="courses.lecture",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="lecture_progresses",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "unique_together": {("user", "lecture")},
            },
        ),
    ]
