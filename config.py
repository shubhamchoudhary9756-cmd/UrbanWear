import os
from datetime import timedelta

# ==================================================
# LOAD ENVIRONMENT VARIABLES FROM .env
# ==================================================

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed. Run: pip install python-dotenv")


BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Environment mode
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
IS_PRODUCTION = FLASK_ENV == "production"


def _get_required_env(key, default=None):
    """Get environment variable. Raise error if critical key missing."""
    value = os.environ.get(key, default)
    if value is None or str(value).strip() == "":
        raise ValueError(
            f"❌ CRITICAL: Environment variable '{key}' is missing!\n"
            f"   Please add it to your .env file."
        )
    return value


class Config:
    # ==================================================
    # FLASK ENVIRONMENT
    # ==================================================
    FLASK_ENV = FLASK_ENV
    DEBUG = not IS_PRODUCTION

    # ==================================================
    # SECURITY - SECRET KEY
    # ==================================================
    SECRET_KEY = _get_required_env("SECRET_KEY")

    # ==================================================
    # DATABASE
    # ==================================================
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(
        BASE_DIR, "instance", "database.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ==================================================
    # RAZORPAY CONFIGURATION
    # ==================================================
    RAZORPAY_KEY_ID = _get_required_env("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET = _get_required_env("RAZORPAY_KEY_SECRET")

    # ==================================================
    # EMAIL CONFIGURATION (GMAIL SMTP)
    # ==================================================
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False

    MAIL_USERNAME = _get_required_env("MAIL_USERNAME")
    MAIL_PASSWORD = _get_required_env("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # ==================================================
    # ADMIN CREDENTIALS
    # ==================================================
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@urbanwear.com")
    ADMIN_PASSWORD = _get_required_env("ADMIN_PASSWORD")

    # ==================================================
    # SESSION SECURITY
    # ==================================================
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = IS_PRODUCTION
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # ==================================================
    # CSRF PROTECTION
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
    # FILE UPLOAD SECURITY
    # ==================================================
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5 MB max upload