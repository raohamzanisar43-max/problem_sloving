"""
Django settings for Novu Opportunity Radar.
"""
import os
from pathlib import Path
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'dev-only-change-me-in-production-novu-radar-2026')
DEBUG = os.getenv('DJANGO_DEBUG', 'true').lower() in ('1', 'true', 'yes')
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0,testserver').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Third party
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    'django_filters',
    # Local apps
    'apps.core',
    'apps.accounts',
    'apps.sources',
    'apps.observations',
    'apps.opportunities',
    'apps.contacts',
    'apps.scoring',
    'apps.exports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'config.wsgi.application'

# Database – SQLite for easy local demo, PostgreSQL for production
if os.getenv('DATABASE_URL') or os.getenv('POSTGRES_DB'):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'novu_radar'),
            'USER': os.getenv('POSTGRES_USER', 'novu'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', 'novu'),
            'HOST': os.getenv('POSTGRES_HOST', 'localhost'),
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Karachi')
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'accounts.User'

# ── Production hardening ──────────────────────────────────────────────────────
# Applied only when DEBUG is off, so local development over plain HTTP is
# unaffected. Each switch can be turned off for deployments that terminate TLS
# somewhere the application cannot see.
def _flag(name, default):
    return os.getenv(name, default).lower() in ('1', 'true', 'yes')


if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = _flag('SECURE_SSL_REDIRECT', 'true')
    SESSION_COOKIE_SECURE = _flag('SESSION_COOKIE_SECURE', 'true')
    CSRF_COOKIE_SECURE = _flag('CSRF_COOKIE_SECURE', 'true')
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '31536000'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = _flag('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'true')
    SECURE_HSTS_PRELOAD = _flag('SECURE_HSTS_PRELOAD', 'false')
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SESSION_COOKIE_HTTPONLY = True
    X_FRAME_OPTIONS = 'DENY'

    if SECRET_KEY.startswith('dev-only-'):
        raise ImproperlyConfigured(
            'DJANGO_SECRET_KEY is still the development default. '
            'Set a long random value before running with DEBUG=False.'
        )

# DRF
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.core.pagination.StandardPagination',
    'PAGE_SIZE': 25,
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ),
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
}

CORS_ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        'CORS_ALLOWED_ORIGINS',
        'http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000'
    ).split(',') if o.strip()
]
CORS_ALLOW_CREDENTIALS = True

# Novu Radar specific
RADAR = {
    'QUALIFICATION_CONFIDENCE': float(os.getenv('QUALIFICATION_CONFIDENCE', '0.75')),
    'COLLECTION_INTERVAL_MINUTES': int(os.getenv('COLLECTION_INTERVAL_MINUTES', '15')),
    'DEFAULT_MARKETS': ['PK', 'GCC'],
    'EXCERPT_RETENTION_DAYS': 90,
    'LLM_PROVIDER': os.getenv('LLM_PROVIDER', 'stub'),  # stub | openai | azure
    'LLM_API_KEY': os.getenv('LLM_API_KEY', ''),
    'LLM_MODEL': os.getenv('LLM_MODEL', 'gpt-4o-mini'),
    'BRAVE_API_KEY': os.getenv('BRAVE_API_KEY', ''),
    'X_BEARER_TOKEN': os.getenv('X_BEARER_TOKEN', ''),
    'REDDIT_CLIENT_ID': os.getenv('REDDIT_CLIENT_ID', ''),
    'REDDIT_CLIENT_SECRET': os.getenv('REDDIT_CLIENT_SECRET', ''),
    'REDDIT_USER_AGENT': os.getenv('REDDIT_USER_AGENT', 'novu-radar/1.0'),
    'MS_GRAPH_CLIENT_ID': os.getenv('MS_GRAPH_CLIENT_ID', ''),
    'MS_GRAPH_CLIENT_SECRET': os.getenv('MS_GRAPH_CLIENT_SECRET', ''),
    'MS_GRAPH_TENANT_ID': os.getenv('MS_GRAPH_TENANT_ID', ''),
    'MS_GRAPH_WORKBOOK_ID': os.getenv('MS_GRAPH_WORKBOOK_ID', ''),
    'MS_GRAPH_TABLE_NAME': os.getenv('MS_GRAPH_TABLE_NAME', 'OpportunityRadar'),
    'ALERT_EMAIL': os.getenv('ALERT_EMAIL', ''),
    'ALERT_MIN_SCORE': int(os.getenv('ALERT_MIN_SCORE', '80')),
    'DUPLICATE_SIMILARITY_THRESHOLD': float(os.getenv('DUPLICATE_SIMILARITY_THRESHOLD', '0.80')),
}

# Celery (optional)
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', CELERY_BROKER_URL)
CELERY_TASK_ALWAYS_EAGER = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'true').lower() in ('1', 'true', 'yes')
CELERY_TIMEZONE = TIME_ZONE

# Periodic schedule, read by `celery -A celery_app beat` (default
# PersistentScheduler — no extra database scheduler package required).
CELERY_BEAT_SCHEDULE = {
    'collect-enabled-sources': {
        'task': 'apps.sources.tasks.collect_all_sources',
        'schedule': timedelta(minutes=RADAR['COLLECTION_INTERVAL_MINUTES']),
    },
    'scan-for-duplicates': {
        'task': 'apps.sources.tasks.find_duplicates',
        'schedule': timedelta(minutes=max(RADAR['COLLECTION_INTERVAL_MINUTES'] * 2, 30)),
    },
    'deliver-outbox': {
        'task': 'apps.exports.delivery.deliver_outbox',
        'schedule': timedelta(minutes=5),
    },
}

# Email
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '25'))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_FROM', 'novu-radar@example.com')
