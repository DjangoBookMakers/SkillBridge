from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
import logging

logger = logging.getLogger("django")


class AdminRequiredMixin(LoginRequiredMixin):
    """
    관리자 권한이 필요한 뷰의 접근 제어 Mixin.

    LoginRequiredMixin을 상속받아 로그인 여부도 함께 체크합니다.
    """

    redirect_url = "learning:dashboard"  # 권한이 없을 때 리디렉션할 URL

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_admin:
            logger.warning(
                f"Non-admin user {request.user.username} attempted to access {self.__class__.__name__}"
            )
            return redirect(self.redirect_url)

        return super().dispatch(request, *args, **kwargs)
