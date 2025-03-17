import os

# 환경 변수에 따라 적절한 설정 파일 로드
# 기본적으로는 개발 환경 설정을 사용
environment = os.environ.get("DJANGO_SETTINGS_MODULE", "config.settings.dev")

if environment == "config.settings.prod":
    from .prod import *
else:
    from .dev import *
