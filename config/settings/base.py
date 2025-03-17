from pathlib import Path
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 기본 경로
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# 보안 키
SECRET_KEY = os.environ.get("SECRET_KEY")

# 디버그 모드 (기본값 False, 환경별 설정에서 오버라이드)
DEBUG = False

ALLOWED_HOSTS = []

# 앱 설정
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.humanize",
    # 내부 앱
    "accounts",
    "admin_portal",
    "courses",
    "learning",
    "payments",
    # 서드파티 앱
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.kakao",
]

# 미들웨어 설정
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

# 기본 URL 설정
ROOT_URLCONF = "config.urls"

# 템플릿 설정
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# 데이터베이스 설정
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# 비밀번호 유효성 검사기
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# 국제화 설정
LANGUAGE_CODE = "ko-kr"
TIME_ZONE = "Asia/Seoul"
USE_I18N = True
USE_TZ = True

# 정적 파일 설정
STATIC_URL = "static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]

# 미디어 파일 설정
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# 기본 자동 필드 설정
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# 사용자 인증 관련 설정
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    # 기본 장고 인증 백엔드
    "django.contrib.auth.backends.ModelBackend",
    # allauth 특정 인증 백엔드
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "accounts:login"

SOCIALACCOUNT_LOGIN_ON_GET = True
ACCOUNT_LOGOUT_ON_GET = True

# 소셜 로그인 설정
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online", "prompt": "select_account"},
    },
    "kakao": {
        "APP": {
            "client_id": os.environ.get("KAKAO_CLIENT_ID", ""),
            "secret": os.environ.get("KAKAO_CLIENT_SECRET", ""),
            "key": "",
        },
        "SCOPE": [],
        "AUTH_PARAMS": {"access_type": "online", "prompt": "select_account"},
    },
}

# 포트원(구 아임포트) 설정
PORTONE_PG = os.environ.get("PORTONE_PG_PROVIDER", "")
PORTONE_SHOP_ID = os.environ.get("PORTONE_SHOP_ID", "")
PORTONE_API_KEY = os.environ.get("PORTONE_API_KEY", "")
PORTONE_API_SECRET = os.environ.get("PORTONE_API_SECRET", "")
