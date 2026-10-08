"""SQLite local para testes; nunca aponta para bases das filiais."""
from .settings import *  # noqa: F403

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "test_despesas.sqlite3"}}  # noqa: F405
MEDIA_ROOT = BASE_DIR / "test_media"
