from django.db import models
from django.conf import settings
from courses.models import Course


class Cart(models.Model):
    """장바구니 모델

    사용자의 장바구니 정보를 저장합니다.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}의 장바구니"

    def get_total_price(self):
        """장바구니 내 모든 상품의 총 가격 계산"""
        return sum(item.course.price for item in self.items.all())

    def get_item_count(self):
        """장바구니 내 상품 개수"""
        return self.items.count()


class CartItem(models.Model):
    """장바구니 아이템 모델

    장바구니에 담긴 개별 과정 정보를 저장합니다.
    """

    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="cart_items"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cart", "course")

    def __str__(self):
        return f"{self.cart.user.username}의 장바구니 - {self.course.title}"


class Payment(models.Model):
    """결제 모델

    과정 구매에 대한 결제 정보를 저장합니다.
    사용자 탈퇴 후에도 매출 통계를 위해 결제 정보는 보존됩니다.
    """

    PAYMENT_STATUS_CHOICES = [
        ("pending", "결제 대기"),
        ("completed", "결제 완료"),
        ("failed", "결제 실패"),
        ("refunded", "환불 완료"),
    ]

    PAYMENT_METHOD_CHOICES = [
        ("card", "신용카드"),
        ("trans", "계좌이체"),
        ("vbank", "가상계좌"),
        ("phone", "휴대폰"),
        ("kakaopay", "카카오페이"),
        ("naverpay", "네이버페이"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="payments",
        null=True,
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.PositiveIntegerField(help_text="결제 금액")
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        null=True,
        blank=True,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending", db_index=True
    )
    merchant_uid = models.CharField(max_length=100, help_text="주문번호", db_index=True)
    imp_uid = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="포트원 거래 고유번호",
        db_index=True,
    )
    refund_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_anonymized = models.BooleanField(
        default=False, help_text="사용자 탈퇴로 인한 익명화 여부"
    )
    anonymized_user_id = models.IntegerField(
        null=True, blank=True, help_text="익명화된 원본 사용자 ID"
    )

    def __str__(self):
        username = (
            self.user.username if self.user else f"탈퇴회원({self.anonymized_user_id})"
        )
        return f"{username}의 {self.course.title} 결제 ({self.get_payment_status_display()})"

    def get_username(self):
        """사용자 이름 반환 (탈퇴한 경우 익명화된 표시)"""
        if self.is_anonymized:
            return f"탈퇴회원({self.anonymized_user_id})"
        return self.user.username if self.user else "알 수 없음"
