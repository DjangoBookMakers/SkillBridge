from django.urls import path
from . import views

app_name = "payments"

urlpatterns = [
    # 장바구니 조회 - 사용자의 장바구니 항목과 총 금액 표시
    path("cart/", views.CartView.as_view(), name="cart_view"),
    # 장바구니에 과정 추가 - 선택한 과정을 사용자 장바구니에 추가
    path(
        "cart/add/<int:course_id>/", views.AddToCartView.as_view(), name="add_to_cart"
    ),
    # 장바구니에서 과정 제거 - 특정 항목을 장바구니에서 삭제
    path(
        "cart/remove/<int:item_id>/",
        views.RemoveFromCartView.as_view(),
        name="remove_from_cart",
    ),
    # 장바구니 비우기 - 장바구니의 모든 항목 삭제
    path("cart/clear/", views.ClearCartView.as_view(), name="clear_cart"),
    # 결제 페이지 - 주문 정보 확인 및 결제 진행
    path("checkout/", views.CheckoutView.as_view(), name="checkout"),
    # 결제 검증 API - 포트원 결제 검증 및 처리
    path("validate/", views.ValidatePaymentView.as_view(), name="validate_payment"),
    # 결제 완료 페이지 - 결제 후 성공 화면 표시
    path("complete/", views.PaymentCompleteView.as_view(), name="payment_complete"),
    # 결제 내역 페이지 - 사용자의 모든 결제 기록 조회
    path("history/", views.PaymentHistoryView.as_view(), name="payment_history"),
    # 결제 상세 페이지 - 개별 결제 건에 대한 상세 정보
    path(
        "detail/<int:payment_id>/",
        views.PaymentDetailView.as_view(),
        name="payment_detail",
    ),
    # 환불 요청 처리 - 결제 취소 및 환불 처리
    path(
        "refund/<int:payment_id>/",
        views.RefundRequestView.as_view(),
        name="refund_request",
    ),
]
