# Generated by Django 5.1.6 on 2025-03-17 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("learning", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="certificate",
            name="certificate_number",
            field=models.CharField(db_index=True, max_length=50, unique=True),
        ),
        migrations.AlterField(
            model_name="certificate",
            name="issued_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="enrolled_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="last_activity_at",
            field=models.DateTimeField(auto_now=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="enrollment",
            name="status",
            field=models.CharField(
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
        migrations.AlterField(
            model_name="lectureprogress",
            name="completed_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="lectureprogress",
            name="is_completed",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name="projectsubmission",
            name="is_passed",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AlterField(
            model_name="projectsubmission",
            name="reviewed_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="projectsubmission",
            name="submitted_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
    ]
