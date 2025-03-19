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
    """사용자 로그인 뷰

    사용자가 아이디와 비밀번호로 로그인할 수 있는 기능을 제공합니다.
    로그인 성공 시 사용자의 로그인 시간을 기록하고,
    실패 시 오류 메시지를 표시합니다.
    """

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
    """사용자 로그아웃 뷰

    사용자가 로그아웃할 수 있는 기능을 제공합니다.
    로그아웃 시 사용자의 로그아웃 시간을 기록하고,
    메인 페이지로 리다이렉트합니다.
    """

    next_page = "/"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            username = request.user.username
            request.user.logout_at = timezone.now()
            request.user.save()
            logger.info(f"User {username} logged out successfully")
        return super().dispatch(request, *args, **kwargs)


class SignupView(CreateView):
    """회원가입 뷰

    새로운 사용자가 계정을 생성할 수 있는 기능을 제공합니다.
    필요한 정보를 입력받아 새 사용자를 생성하고,
    성공 시 로그인 페이지로 리다이렉트합니다.
    """

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
    """사용자 프로필 페이지 뷰

    로그인한 사용자의 프로필 정보와 구매 내역을 보여주는 페이지입니다.
    개인 정보, 계정 설정, 구매한 과정 목록 등을 확인할 수 있습니다.
    """

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
    """사용자 프로필 수정 뷰

    로그인한 사용자가 자신의 프로필 정보를 수정할 수 있는 기능을 제공합니다.
    이메일, 이름, 프로필 이미지, 전화번호 등을 업데이트할 수 있습니다.
    """

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
    """비밀번호 변경 뷰

    로그인한 사용자가 자신의 비밀번호를 변경할 수 있는 기능을 제공합니다.
    현재 비밀번호 확인 후 새 비밀번호로 변경하며,
    성공 시 프로필 페이지로 리다이렉트합니다.
    """

    template_name = "accounts/change_password.html"
    form_class = CustomPasswordChangeForm
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        messages.success(self.request, "비밀번호가 성공적으로 변경되었습니다.")
        return super().form_valid(form)


class DeleteAccountView(LoginRequiredMixin, View):
    """계정 삭제 뷰

    로그인한 사용자가 자신의 계정을 삭제할 수 있는 기능을 제공합니다.
    계정 삭제 시 프로필 이미지와 소셜 계정 연결 정보도 함께 삭제됩니다.
    """

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
