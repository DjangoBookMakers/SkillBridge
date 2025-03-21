# Generated by Django 5.1.6 on 2025-03-17 11:52

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_alter_payment_amount"),
    ]

    operations = [
        migrations.AlterField(
            model_name="payment",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name="payment",
            name="imp_uid",
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text="포트원 거래 고유번호",
                max_length=100,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="merchant_uid",
            field=models.CharField(db_index=True, help_text="주문번호", max_length=100),
        ),
        migrations.AlterField(
            model_name="payment",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("card", "신용카드"),
                    ("trans", "계좌이체"),
                    ("vbank", "가상계좌"),
                    ("phone", "휴대폰"),
                    ("kakaopay", "카카오페이"),
                    ("naverpay", "네이버페이"),
                ],
                db_index=True,
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="payment",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("pending", "결제 대기"),
                    ("completed", "결제 완료"),
                    ("failed", "결제 실패"),
                    ("refunded", "환불 완료"),
                ],
                db_index=True,
                default="pending",
                max_length=20,
            ),
        ),
    ]
