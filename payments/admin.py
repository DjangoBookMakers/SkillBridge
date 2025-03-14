from django.contrib import admin
from .models import Cart, CartItem, Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "course",
        "amount",
        "payment_status",
        "payment_method",
        "created_at",
    )
    list_filter = ("payment_status", "payment_method", "created_at")
    search_fields = (
        "user__username",
        "user__email",
        "course__title",
        "merchant_uid",
        "imp_uid",
    )
    date_hierarchy = "created_at"
    readonly_fields = ("merchant_uid", "imp_uid", "created_at", "updated_at")


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "get_item_count", "get_total_price", "created_at")
    search_fields = ("user__username", "user__email")
    inlines = [CartItemInline]

    def get_item_count(self, obj):
        return obj.get_item_count()

    get_item_count.short_description = "아이템 수"

    def get_total_price(self, obj):
        return f"{obj.get_total_price():,} 원"

    get_total_price.short_description = "총 금액"
