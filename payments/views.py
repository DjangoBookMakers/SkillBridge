from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone
import json
import logging

from courses.models import Course
from learning.models import Enrollment
from .models import Cart, CartItem, Payment
from .payment_client import payment_client

logger = logging.getLogger("django")


@login_required
def cart_view(request):
    """장바구니 조회 페이지"""
    # 사용자의 장바구니를 가져오거나 새로 생성
    cart, created = Cart.objects.get_or_create(user=request.user)
    if created:
        logger.info(f"New cart created for user {request.user.username}")

    # 장바구니 아이템과 관련 과정 정보 가져오기
    cart_items = CartItem.objects.filter(cart=cart).select_related("course")

    # 장바구니 합계 계산
    total_price = cart.get_total_price()

    logger.debug(
        f"Cart viewed: user={request.user.username}, items={cart_items.count()}, total={total_price}"
    )

    context = {
        "cart": cart,
        "cart_items": cart_items,
        "total_price": total_price,
    }

    return render(request, "payments/cart.html", context)


@login_required
def add_to_cart(request, course_id):
    """장바구니에 과정 추가"""
    course = get_object_or_404(Course, id=course_id)

    # 이미 수강 중인지 확인
    if (
        hasattr(request.user, "enrollments")
        and request.user.enrollments.filter(course=course).exists()
    ):
        logger.info(
            f"User {request.user.username} attempted to add already enrolled course to cart: {course.title}"
        )
        messages.warning(request, f"이미 수강 중인 과정입니다: {course.title}")
        return redirect("course_detail", course_id=course.id)

    # 사용자의 장바구니를 가져오거나 새로 생성
    cart, created = Cart.objects.get_or_create(user=request.user)

    # 장바구니에 이미 있는지 확인
    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, course=course)

    if item_created:
        messages.success(request, f'"{course.title}" 과정이 장바구니에 추가되었습니다.')
    else:
        messages.info(request, f'"{course.title}" 과정은 이미 장바구니에 있습니다.')

    # AJAX 요청인 경우 JSON 응답 반환
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": (
                    f'"{course.title}" 과정이 장바구니에 추가되었습니다.'
                    if item_created
                    else f'"{course.title}" 과정은 이미 장바구니에 있습니다.'
                ),
                "cart_count": cart.get_item_count(),
            }
        )

    # 일반 요청인 경우 리다이렉트
    return redirect("cart_view")


@login_required
def remove_from_cart(request, item_id):
    """장바구니에서 과정 제거"""
    cart_item = get_object_or_404(CartItem, id=item_id)

    # 해당 항목이 사용자의 장바구니에 있는지 확인
    if cart_item.cart.user != request.user:
        messages.error(request, "해당 항목을 삭제할 권한이 없습니다.")
        return redirect("cart_view")

    course_title = cart_item.course.title
    cart_item.delete()

    messages.success(request, f'"{course_title}" 과정이 장바구니에서 제거되었습니다.')

    # AJAX 요청인 경우 JSON 응답 반환
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": f'"{course_title}" 과정이 장바구니에서 제거되었습니다.',
                "cart_count": cart_item.cart.get_item_count(),
            }
        )

    # 일반 요청인 경우 리다이렉트
    return redirect("cart_view")


@login_required
def clear_cart(request):
    """장바구니 비우기"""
    cart, created = Cart.objects.get_or_create(user=request.user)

    # 장바구니 비우기
    CartItem.objects.filter(cart=cart).delete()

    messages.success(request, "장바구니가 비워졌습니다.")

    # AJAX 요청인 경우 JSON 응답 반환
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "success": True,
                "message": "장바구니가 비워졌습니다.",
            }
        )

    # 일반 요청인 경우 리다이렉트
    return redirect("cart_view")


@login_required
def checkout(request):
    """결제 페이지"""
    # 사용자의 장바구니를 가져오거나 새로 생성
    cart, _created = Cart.objects.get_or_create(user=request.user)

    # 장바구니 아이템과 관련 과정 정보 가져오기
    cart_items = CartItem.objects.filter(cart=cart).select_related("course")

    # 장바구니가 비어있는 경우
    if not cart_items.exists():
        logger.warning(
            f"User {request.user.username} attempted checkout with empty cart"
        )
        messages.warning(request, "장바구니가 비어있습니다.")
        return redirect("cart_view")

    # 장바구니 합계 계산
    total_price = cart.get_total_price()

    # 결제 정보 생성 (포트원 API 호출)
    course_titles = ", ".join([item.course.title for item in cart_items[:3]])
    if len(cart_items) > 3:
        course_titles += f" 외 {len(cart_items) - 3}개"

    payment_name = f"{course_titles} - 스킬브릿지"
    merchant_uid = payment_client.generate_merchant_uid()

    logger.info(
        f"Checkout initiated: user={request.user.username}, items={cart_items.count()}, total={total_price}, merchant_uid={merchant_uid}"
    )

    context = {
        "cart_items": cart_items,
        "total_price": total_price,
        "payment_name": payment_name,
        "merchant_uid": merchant_uid,
        "portone_shop_id": settings.PORTONE_SHOP_ID,
        "portone_pg": settings.PORTONE_PG,
    }

    return render(request, "payments/checkout.html", context)


@login_required
def validate_payment(request):
    """결제 검증 API"""
    if request.method != "POST":
        logger.warning(f"Invalid request method for validate_payment: {request.method}")
        return JsonResponse({"success": False, "message": "잘못된 요청 방식입니다."})

    try:
        data = json.loads(request.body)
        imp_uid = data.get("imp_uid")
        merchant_uid = data.get("merchant_uid")
        amount = data.get("amount")

        # 필수 파라미터 확인
        if not all([imp_uid, merchant_uid, amount]):
            logger.error(
                f"Missing required parameters: imp_uid={imp_uid}, merchant_uid={merchant_uid}, amount={amount}"
            )
            return JsonResponse(
                {"success": False, "message": "필수 파라미터가 누락되었습니다."}
            )

        logger.info(
            f"Validating payment: imp_uid={imp_uid}, merchant_uid={merchant_uid}, amount={amount}"
        )

        # 결제 검증 (포트원 API 호출)
        is_valid, result = payment_client.verify_payment(imp_uid, merchant_uid, amount)

        if is_valid:
            logger.info(f"Payment validation successful: {merchant_uid}")
            # 결제 성공 처리 로직
            with transaction.atomic():
                # 사용자의 장바구니 가져오기
                cart = Cart.objects.get(user=request.user)
                cart_items = CartItem.objects.filter(cart=cart).select_related("course")

                # 결제 정보 저장
                payment_method = result.get("pay_method", "")

                # 과정별로 결제 내역 생성 및 수강 등록
                for cart_item in cart_items:
                    course = cart_item.course

                    # 결제 내역 생성
                    payment = Payment.objects.create(
                        user=request.user,
                        course=course,
                        amount=course.price,
                        payment_method=payment_method,
                        payment_status="completed",
                        merchant_uid=merchant_uid,
                        imp_uid=imp_uid,
                    )
                    logger.info(
                        f"Payment record created: id={payment.id}, user={request.user.username}, course={course.title}"
                    )

                    # 수강 등록
                    enrollment, created = Enrollment.objects.get_or_create(
                        user=request.user,
                        course=course,
                        defaults={"status": "enrolled", "progress_percentage": 0},
                    )
                    if created:
                        logger.info(
                            f"New enrollment created: user={request.user.username}, course={course.title}"
                        )
                    else:
                        logger.info(
                            f"Existing enrollment found: user={request.user.username}, course={course.title}"
                        )

                # 장바구니 비우기
                items_count = cart_items.count()
                cart_items.delete()
                logger.info(
                    f"Cart cleared for user {request.user.username}: {items_count} items removed"
                )

            # 결제 완료 페이지 URL
            redirect_url = reverse("payment_complete")

            return JsonResponse(
                {
                    "success": True,
                    "message": "결제가 성공적으로 처리되었습니다.",
                    "redirect_url": redirect_url,
                }
            )
        else:
            # 결제 검증 실패
            logger.error(f"Payment validation failed: {result}")
            return JsonResponse({"success": False, "message": result})

    except Exception as e:
        logger.exception(f"Error during payment validation: {str(e)}")
        return JsonResponse(
            {"success": False, "message": f"결제 처리 중 오류가 발생했습니다: {str(e)}"}
        )


@login_required
def payment_complete(request):
    """결제 완료 페이지"""
    # 최근 결제 내역
    recent_payments = Payment.objects.filter(
        user=request.user, payment_status="completed"
    ).order_by("-created_at")[:5]

    context = {
        "recent_payments": recent_payments,
    }

    return render(request, "payments/payment_complete.html", context)


@login_required
def payment_history(request):
    """결제 내역 페이지"""
    # 사용자의 모든 결제 내역
    payments = Payment.objects.filter(user=request.user).order_by("-created_at")

    context = {
        "payments": payments,
    }

    return render(request, "payments/payment_history.html", context)


@login_required
def payment_detail(request, payment_id):
    """결제 상세 페이지"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    context = {
        "payment": payment,
    }

    return render(request, "payments/payment_detail.html", context)


@login_required
def refund_request(request, payment_id):
    """환불 요청 처리"""
    payment = get_object_or_404(Payment, id=payment_id, user=request.user)

    # 이미 환불된 경우
    if payment.payment_status == "refunded":
        logger.warning(
            f"User {request.user.username} attempted to refund already refunded payment: {payment_id}"
        )
        messages.error(request, "이미 환불된 결제입니다.")
        return redirect("payment_detail", payment_id=payment.id)

    if request.method == "POST":
        refund_reason = request.POST.get("refund_reason", "").strip()

        if not refund_reason:
            logger.warning(
                f"Refund request missing reason: user={request.user.username}, payment={payment_id}"
            )
            messages.error(request, "환불 사유를 입력해주세요.")
            return redirect("payment_detail", payment_id=payment.id)

        try:
            logger.info(
                f"Processing refund: payment={payment_id}, user={request.user.username}, amount={payment.amount}, reason={refund_reason}"
            )
            with transaction.atomic():
                # 부분 환불 금액 계산
                refund_amount = payment.amount

                # 포트원 API 호출하여 환불 처리
                is_successful, result = payment_client.refund_payment(
                    reason=refund_reason,
                    imp_uid=payment.imp_uid,
                    merchant_uid=payment.merchant_uid,
                    amount=refund_amount,
                )

                if is_successful:
                    # 환불 성공 시 결제 정보 업데이트
                    payment.refund_reason = refund_reason
                    payment.payment_status = "refunded"
                    payment.updated_at = timezone.now()
                    payment.save()

                    # 수강 등록 정보도 삭제
                    Enrollment.objects.filter(
                        user=request.user, course=payment.course
                    ).delete()

                    messages.success(request, "환불이 성공적으로 처리되었습니다.")
                else:
                    messages.error(
                        request, f"환불 처리 중 오류가 발생했습니다: {result}"
                    )
                    return redirect("payment_detail", payment_id=payment.id)

                return redirect("payment_history")

        except Exception as e:
            logger.exception("환불 처리 중 오류 발생")
            messages.error(request, f"환불 처리 중 오류가 발생했습니다: {str(e)}")
            return redirect("payment_detail", payment_id=payment.id)

    # GET 요청은 결제 상세 페이지로 리다이렉트
    return redirect("payment_detail", payment_id=payment.id)
