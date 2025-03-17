from .base import *

# 개발 환경 설정
DEBUG = True

ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

# 개발 환경에서의 로깅 설정
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": True,
        },
    },
}

# 개발 환경에서만 필요한 설정이나 앱이 있다면 여기에 추가
