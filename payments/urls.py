from django.urls import path
from . import views

urlpatterns = [
    # 장바구니 관련 URL
    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/<int:course_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
    # 결제 관련 URL
    path("checkout/", views.checkout, name="checkout"),
    path("validate/", views.validate_payment, name="validate_payment"),
    path("complete/", views.payment_complete, name="payment_complete"),
    path("history/", views.payment_history, name="payment_history"),
    path("detail/<int:payment_id>/", views.payment_detail, name="payment_detail"),
]
