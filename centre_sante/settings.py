"""
Configuration du projet Django — Gestion d'un centre de santé / clinique.
"""
import os
from pathlib import Path
from datetime import timedelta

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "changez-moi-en-production-cle-aleatoire")
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",

    "sante",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "centre_sante.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

WSGI_APPLICATION = "centre_sante.wsgi.application"

# ---------------------------------------------------------
# Base de données — SQLite par défaut (démo), PostgreSQL en production
# via la variable d'environnement DATABASE_URL (voir README.md)
# ---------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "centre_sante.db",
    }
}

# Exemple de configuration PostgreSQL (à activer en décommentant, cf README) :
# DATABASES["default"] = {
#     "ENGINE": "django.db.backends.postgresql",
#     "NAME": os.getenv("DB_NAME", "centre_sante"),
#     "USER": os.getenv("DB_USER", "postgres"),
#     "PASSWORD": os.getenv("DB_PASSWORD", ""),
#     "HOST": os.getenv("DB_HOST", "localhost"),
#     "PORT": os.getenv("DB_PORT", "5432"),
# }

AUTH_USER_MODEL = "sante.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 6}},
]

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PARSER_CLASSES": (
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ),
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=2),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# ---------------------------------------------------------
# CORS — accès depuis le frontend statique (http://localhost:5500)
# ---------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = True
