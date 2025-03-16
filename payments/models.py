from django.db import models
from django.conf import settings
from courses.models import Course


class Cart(models.Model):
    """장바구니 모델"""

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
    """장바구니 아이템 모델"""

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
    """결제 모델"""

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
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="payments"
    )
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, related_name="payments"
    )
    amount = models.PositiveIntegerField(help_text="결제 금액")
    payment_method = models.CharField(
        max_length=20, choices=PAYMENT_METHOD_CHOICES, null=True, blank=True
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )
    merchant_uid = models.CharField(max_length=100, help_text="주문번호")
    imp_uid = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        help_text="포트원 거래 고유번호",
    )
    refund_reason = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}의 {self.course.title} 결제 ({self.get_payment_status_display()})"
