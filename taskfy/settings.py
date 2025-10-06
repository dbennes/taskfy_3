"""
Django settings for taskfy project.

Gerado por 'django-admin startproject' usando Django 5.2.3.
"""

from pathlib import Path
import os
from datetime import timedelta

# === Caminhos base ===
BASE_DIR = Path(__file__).resolve().parent.parent

# === Segurança / Debug ===
SECRET_KEY = 'django-insecure-ek1fnjxzic4aol1_+hqh)bb2xbpduj*dhlp@%^=xcbgh#qs&$t'
DEBUG = True
ALLOWED_HOSTS = ['*']

# (Opcional DEV) Evita o aviso de COOP em HTTP. Em produção (HTTPS), remova/ajuste.
if DEBUG:
    SECURE_CROSS_ORIGIN_OPENER_POLICY = None

# === Apps instalados ===
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'django.contrib.humanize',

    'rest_framework',
    'corsheaders',

    # Mantido (fila RQ)
    'django_rq',
    "jobcards.apps.JobcardsConfig",  # << use o AppConfig
]

# =================================================
# Redis: /1 para cache | /0 para filas RQ
REDIS_URL_CACHE = os.environ.get("REDIS_URL_CACHE", "redis://127.0.0.1:6379/1")
REDIS_URL_RQ    = os.environ.get("REDIS_URL_RQ",    "redis://127.0.0.1:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL_CACHE,
        "OPTIONS": {"CLIENT_CLASS": "django_redis.client.DefaultClient"},
        "TIMEOUT": 60 * 60 * 6,  # 6h
        "KEY_PREFIX": "jobcards",
    }
}

# Filas RQ
RQ_QUEUES = {
    "default": {"URL": REDIS_URL_RQ, "DEFAULT_TIMEOUT": 3600},
    "pdf":     {"URL": REDIS_URL_RQ, "DEFAULT_TIMEOUT": 3600},
}
# =================================================

# === Middleware ===
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',

    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',

    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    #"jobcards.middleware.ForcePasswordChangeMiddleware",  # << aqui sim
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# === CORS (dev) ===
CORS_ALLOW_ALL_ORIGINS = True

ROOT_URLCONF = 'taskfy.urls'

# === Templates ===
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # templates globais
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'taskfy.wsgi.application'

# === Banco de Dados ===
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'taskfy',
        'USER': 'postgres',
        'PASSWORD': 'Mabu@2030!',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# === Password validators ===
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# === i18n ===
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# === Arquivos estáticos (CSS/JS/IMG) ===
# Use {% load static %} e {% static 'caminho/arquivo.ext' %}
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')              # destino do collectstatic
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]            # fontes locais (ex.: static/assets/*)

# WhiteNoise: gzip/brotli + manifest para cache busting
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# === Media / Backups de PDF ===
# OBS: você já usa jobcard_backups como MEDIA_ROOT. Mantido para não quebrar rotas existentes.
MEDIA_URL = '/jobcard_backups/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'jobcard_backups')

# Compatibilidade com código legado
JOB_BACKUP_DIR = os.path.join(BASE_DIR, 'jobcard_backups')
os.makedirs(JOB_BACKUP_DIR, exist_ok=True)

# === Pastas auxiliares usadas pelo diagnóstico e geração de PDF ===
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
PDF_TEMP_DIR = os.path.join(BASE_DIR, 'tmp')  # temp para headers/footers HTML etc.
BARCODES_DIR = os.path.join(BASE_DIR, 'static', 'barcodes')
BACKUPS_DIR = JOB_BACKUP_DIR  # mesma pasta dos backups

for _p in (LOGS_DIR, PDF_TEMP_DIR, BARCODES_DIR, BACKUPS_DIR):
    os.makedirs(_p, exist_ok=True)

# === Caminho do wkhtmltopdf (ajuste conforme sua instalação no Windows) ===
# Ex.: D:\taskfy\wkhtmltopdf\bin\wkhtmltopdf.exe
WKHTMLTOPDF_BIN = str((BASE_DIR / "wkhtmltopdf" / "bin" / "wkhtmltopdf.exe").resolve())

# === REST/JWT ===
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=3650),  # 10 anos
    'REFRESH_TOKEN_LIFETIME': timedelta(days=3650),
}

# Levante o limite de campos em formulários grandes (JobCard Editor/Wizard)
# Use um valor confortavelmente acima do seu maior formulário.
# DATA_UPLOAD_MAX_NUMBER_FIELDS = int(os.getenv("DATA_UPLOAD_MAX_NUMBER_FIELDS", "50000"))

# Se a sua versão do Django aceitar, você também pode remover o limite:
# (Se der erro ao usar None na sua versão, mantenha o inteiro alto acima)
DATA_UPLOAD_MAX_NUMBER_FIELDS = None


# === Email — abolir SMTP e usar teu provider via backend ===
EMAIL_BACKEND = "jobcards.email_backends_graph.GraphOnlyEmailBackend"

MS_GRAPH = {
    "TENANT_ID": "#",
    "CLIENT_ID": "#",
    "CLIENT_SECRET": "#",
}

EMAIL_SENDER = "suporte.taskfy@utci.com.br"
DEFAULT_FROM_EMAIL = "Taskfy <suporte.taskfy@utci.com.br>"

# (opcional, mas recomendado em prod)
# MS_GRAPH = {
#   "TENANT_ID": os.getenv("GRAPH_TENANT_ID"),
#   "CLIENT_ID": os.getenv("GRAPH_CLIENT_ID"),
#   "CLIENT_SECRET": os.getenv("GRAPH_CLIENT_SECRET"),
# }
# EMAIL_SENDER = os.getenv("GRAPH_SENDER", "suporte.taskfy@utci.com.br")

SITE_URL = os.getenv("SITE_URL", "http://127.0.0.1:8080").rstrip("/")

# === Auth redirects ===
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"