# Generated by Django 5.1.6 on 2025-03-17 08:47

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0002_alter_lecture_duration"),
    ]

    operations = [
        migrations.RenameField(
            model_name="lecture",
            old_name="video_url",
            new_name="video_file",
        ),
    ]
