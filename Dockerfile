FROM python:3.13-slim

WORKDIR /app

# 시스템 패키지 설치
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 의존성 설치
COPY pyproject.toml .
RUN pip install --upgrade pip \
    && pip install pdm \
    && pdm install --no-lock --no-editable

# 애플리케이션 복사
COPY . .

# 정적 파일 수집
RUN python manage.py collectstatic --noinput

# gunicorn 설치
RUN pip install gunicorn

# 포트 설정
EXPOSE 8000

# 환경변수 설정
ENV DJANGO_SETTINGS_MODULE=config.settings.prod

# 실행 명령
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "config.wsgi:application"]
