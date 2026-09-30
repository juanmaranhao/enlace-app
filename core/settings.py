"""Configuração local do Enlace; segredos vêm somente do .env desta instalação."""
from pathlib import Path

import dj_database_url
from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent
VERSAO = 'v0.1.0'
SECRET_KEY = config("DJANGO_SECRET_KEY", default="unsafe-local-only-change-me")
DEBUG = config("DJANGO_DEBUG", default=False, cast=bool)
if not DEBUG and SECRET_KEY == 'unsafe-local-only-change-me':
    raise RuntimeError('Configure DJANGO_SECRET_KEY nesta instalação.')
ALLOWED_HOSTS = [host.strip() for host in config("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost").split(",") if host.strip()]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "apps.projetos", "apps.arquitetura", "apps.assistente",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.LocalCSPMiddleware",
]
ROOT_URLCONF = "core.urls"
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "base_templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug", "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages",
        "core.context_processors.brand",
    ]},
}]
WSGI_APPLICATION = "core.wsgi.application"
ASGI_APPLICATION = "core.asgi.application"

database_url = config("DATABASE_URL", default="").strip()
if not DEBUG and not database_url:
    raise RuntimeError("DATABASE_URL é obrigatório fora do modo local de desenvolvimento.")
DATABASES = {"default": dj_database_url.parse(database_url) if database_url else {
    "ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3",
}}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "base_static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'enlace_session'
CSRF_COOKIE_NAME = 'enlace_csrf'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "carteira"
LOGOUT_REDIRECT_URL = "login"

configured_roots = config("ENLACE_ALLOWED_ROOTS", default="").strip()
ENLACE_ALLOWED_ROOTS = [Path(part).resolve() for part in configured_roots.split(";") if part.strip()] if configured_roots else [BASE_DIR.parent.parent.resolve()]
JEV_IA = config('JEV_IA', default='')
JEV_API_URL = config('JEV_API_URL',default='https://api.typesafe.ai/v1/systemone')
JEV_MODEL = config('JEV_MODEL',default='jev-1.13.0')
JEV_CONFIGURED = bool(JEV_IA)
OPENAI_API_KEY = config('OPENAI_API_KEY',default='')
OPENAI_TEXT_MODEL = config('OPENAI_TEXT_MODEL',default='')
TEXT_CONFIGURED = bool(OPENAI_API_KEY and OPENAI_TEXT_MODEL)

