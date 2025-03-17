from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.files.storage import default_storage
from django.utils import timezone

from payments.models import Payment
from .forms import LoginForm, SignupForm, ProfileEditForm, CustomPasswordChangeForm


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                user.login_at = timezone.now()
                user.save()
                return redirect("/")  # 사용자 -> 메인 화면
            else:
                messages.error(request, "아이디 또는 비밀번호가 올바르지 않습니다.")
        else:
            messages.error(request, "입력 정보를 확인해주세요.")
    else:
        form = LoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    if request.user.is_authenticated:
        from django.contrib.messages import get_messages

        storage = get_messages(request)
        storage.used = True

        request.user.logout_at = timezone.now()
        request.user.save()
        logout(request)
    return redirect("/")


def signup_view(request):
    if request.method == "POST":
        form = SignupForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("accounts:login")
    else:
        form = SignupForm()

    return render(request, "accounts/signup.html", {"form": form})


@login_required
def profile_view(request):
    # 사용자의 실제 결제 내역 가져오기
    purchases = []

    # 완료된 결제 내역에서 과정 정보 가져오기
    payments = (
        Payment.objects.filter(user=request.user, payment_status="completed")
        .select_related("course")
        .order_by("-created_at")
    )

    for payment in payments:
        purchases.append(
            {
                "course": payment.course,
                "purchase_date": payment.created_at,
                "price": payment.amount,
                "status": payment.get_payment_status_display(),
            }
        )

    context = {
        "user": request.user,
        "purchases": purchases,
    }
    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit_view(request):
    if request.method == "POST":
        form = ProfileEditForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "프로필이 성공적으로 업데이트되었습니다.")
            return redirect("accounts:profile")
    else:
        form = ProfileEditForm(instance=request.user)

    context = {
        "form": form,
    }
    return render(request, "accounts/profile_edit.html", context)


@login_required
def change_password_view(request):
    if request.method == "POST":
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            # 세션 유지를 위해 필요
            update_session_auth_hash(request, user)
            messages.success(request, "비밀번호가 성공적으로 변경되었습니다.")
            return redirect("accounts:profile")
    else:
        form = CustomPasswordChangeForm(request.user)

    context = {
        "form": form,
    }
    return render(request, "accounts/change_password.html", context)


@login_required
def delete_account_view(request):
    if request.method == "POST":
        user = request.user

        # 프로필 이미지 삭제
        if user.profile_image:
            # Django의 storage 시스템을 사용하여 파일 삭제
            default_storage.delete(user.profile_image.name)

        # 소셜 계정 연결 확인 및 삭제
        social_accounts = request.user.socialaccount_set.all()
        if social_accounts.exists():
            social_accounts.delete()

        # 사용자 계정 삭제
        logout(request)
        user.delete()

        messages.success(request, "회원 탈퇴가 완료되었습니다.")
        return redirect("accounts:login")

    # GET 요청시 확인 페이지 표시
    return render(request, "accounts/delete_account.html")
