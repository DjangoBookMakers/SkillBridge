from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import redirect
import logging

logger = logging.getLogger("django")


class AdminRequiredMixin(LoginRequiredMixin):
    """
    관리자 권한이 필요한 뷰의 접근 제어 Mixin.

    LoginRequiredMixin을 상속받아 로그인 여부도 함께 체크합니다.
    관리자 권한 여부를 검사합니다.
    관리자가 아닌 사용자가 접근할 경우 설정된 URL로 리다이렉트합니다.
    """

    redirect_url = "learning:dashboard"

    def dispatch(self, request, *args, **kwargs):
        """요청을 처리하기 전에 관리자 권한을 검사

        사용자가 로그인되어 있고 관리자인 경우에만 뷰 처리를 진행하고,
        그렇지 않은 경우 redirect_url로 리다이렉트합니다.
        """
        if not request.user.is_admin:
            logger.warning(
                f"Non-admin user {request.user.username} attempted to access {self.__class__.__name__}"
            )
            return redirect(self.redirect_url)

        return super().dispatch(request, *args, **kwargs)
