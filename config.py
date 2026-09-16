import os
from datetime import timedelta

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Environment mode
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
IS_PRODUCTION = FLASK_ENV == "production"


def _get_required_env(key, default=None):
    value = os.environ.get(key, default)
    if value is None or str(value).strip() == "":
        raise ValueError(
            f"❌ CRITICAL: Environment variable '{key}' is missing!\n"
            f"   Please add it to your .env file."
        )
    return value


class Config:
    FLASK_ENV = FLASK_ENV
    DEBUG = not IS_PRODUCTION

    # ==================================================
    # BRAND
    # ==================================================
    SITE_NAME = "Zenith"
    SITE_TAGLINE = "Wear the Peak"

    # ==================================================
    # SECURITY
    # ==================================================
    SECRET_KEY = _get_required_env("SECRET_KEY")

    # ==================================================
    # DATABASE — PostgreSQL in Production, SQLite in Dev
    # ==================================================
    _db_url = os.environ.get("DATABASE_URL", "")

    if _db_url:
        # Render provides postgres:// but SQLAlchemy needs postgresql://
        if _db_url.startswith("postgres://"):
            _db_url = _db_url.replace("postgres://", "postgresql://", 1)
        SQLALCHEMY_DATABASE_URI = _db_url
    else:
        SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
            BASE_DIR, "instance", "database.db"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # ==================================================
    # RAZORPAY
    # ==================================================
    RAZORPAY_KEY_ID = _get_required_env("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = _get_required_env("RAZORPAY_KEY_SECRET")

    # ==================================================
    # EMAIL
    # ==================================================
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = _get_required_env("MAIL_USERNAME")
    MAIL_PASSWORD = _get_required_env("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # ==================================================
    # ADMIN
    # ==================================================
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@zenith.com")
    ADMIN_PASSWORD = _get_required_env("ADMIN_PASSWORD")

    # ==================================================
    # SESSION
    # ==================================================
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ==================================================
    # CSRF
    # ==================================================
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = IS_PRODUCTION

    # ==================================================
    # RATE LIMITING
    # ==================================================
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_HEADERS_ENABLED = True

    # ==================================================
    # FILE UPLOAD
    # ==================================================
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024