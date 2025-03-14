from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse

from courses.models import Course
from .models import Cart, CartItem


@login_required
def cart_view(request):
    """장바구니 조회 페이지"""
    # 사용자의 장바구니를 가져오거나 새로 생성
    cart, _created = Cart.objects.get_or_create(user=request.user)

    # 장바구니 아이템과 관련 과정 정보 가져오기
    cart_items = CartItem.objects.filter(cart=cart).select_related("course")

    # 장바구니 합계 계산
    total_price = cart.get_total_price()

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
