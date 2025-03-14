from django.urls import path
from . import views

urlpatterns = [
    # 장바구니 관련 URL
    path("cart/", views.cart_view, name="cart_view"),
    path("cart/add/<int:course_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/remove/<int:item_id>/", views.remove_from_cart, name="remove_from_cart"),
    path("cart/clear/", views.clear_cart, name="clear_cart"),
]
