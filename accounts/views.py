from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.files.storage import default_storage
from django.views.generic import CreateView, TemplateView, UpdateView, View
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.utils import timezone
import logging

from payments.models import Payment
from .forms import LoginForm, SignupForm, ProfileEditForm, CustomPasswordChangeForm
from .models import User

logger = logging.getLogger("django")


class LoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        # 로그인 시간 저장
        user = form.get_user()
        user.login_at = timezone.now()
        user.save()
        logger.info(f"User {user.username} logged in successfully.")
        return super().form_valid(form)

    def form_invalid(self, form):
        username = form.cleaned_data.get("username", "unknown")
        logger.warning(f"Failed login attempt for username: {username}")
        messages.error(self.request, "아이디 또는 비밀번호가 올바르지 않습니다.")
        return super().form_invalid(form)


class LogoutView(auth_views.LogoutView):
    next_page = "/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            username = request.user.username
            request.user.logout_at = timezone.now()
            request.user.save()
            logger.info(f"User {username} logged out successfully")
        return super().dispatch(request, *args, **kwargs)


class SignupView(CreateView):
    model = User
    form_class = SignupForm
    template_name = "accounts/signup.html"
    success_url = reverse_lazy("accounts:login")

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(f"New user registered: {self.object.username}")
        messages.success(self.request, "회원가입이 완료되었습니다. 로그인해주세요.")
        return response


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # 사용자의 실제 결제 내역 가져오기
        purchases = []

        # 완료된 결제 내역에서 과정 정보 가져오기
        payments = (
            Payment.objects.filter(user=self.request.user, payment_status="completed")
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

        context["user"] = self.request.user
        context["purchases"] = purchases
        return context


class ProfileEditView(LoginRequiredMixin, UpdateView):
    model = User
    template_name = "accounts/profile_edit.html"
    form_class = ProfileEditForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset=None):
        return self.request.user

    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(f"User {self.request.user.username} updated own profile")
        messages.success(self.request, "프로필이 성공적으로 업데이트되었습니다.")
        return response


class ChangePasswordView(auth_views.PasswordChangeView):
    template_name = "accounts/change_password.html"
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "비밀번호가 성공적으로 변경되었습니다.")
        return super().form_valid(form)


class DeleteAccountView(LoginRequiredMixin, View):
    template_name = "accounts/delete_account.html"

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        user = request.user
        username = user.username

        # 프로필 이미지 삭제
        if user.profile_image:
            default_storage.delete(user.profile_image.name)
            logger.info(f"Profile image deleted for user: {username}")

        # 소셜 계정 연결 확인 및 삭제
        social_accounts = request.user.socialaccount_set.all()
        if social_accounts.exists():
            logger.info(
                f"Deleting {social_accounts.count()} social accounts for user: {username}"
            )
            social_accounts.delete()

        # 사용자 계정 삭제
        logger.warning(f"User account deleted: {username}")
        user.delete()

        messages.success(request, "회원 탈퇴가 완료되었습니다.")
        return redirect("accounts:login")
