import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = "urbanwear_secret_key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "database.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # ==================================================
    # RAZORPAY CONFIGURATION (TEST MODE)
    # ==================================================
    
    RAZORPAY_KEY_ID = "rzp_test_TaDQJc90PDLyiR"
    RAZORPAY_KEY_SECRET = "9gkxXiAkzsxSFuFSfnxXcwec"
    
    # ==================================================
    # EMAIL CONFIGURATION (GMAIL SMTP)
    # ==================================================
    
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    
    # ⚠️ APNA GMAIL ADDRESS DAALO (jispe App Password banaya)
    MAIL_USERNAME = "shubhamchoudhary9756@gmail.com"
    
    # ⚠️ YEH AAPKA APP PASSWORD HAI
    MAIL_PASSWORD = "thpx dyqw rxpk hpst"
    
    # ⚠️ SAME GMAIL ADDRESS (MAIL_USERNAME jaisa hi)
    MAIL_DEFAULT_SENDER = "shubhamchoudhary9756@gmail.com"
    
    # ==================================================
    # SECURITY CONFIGURATION
    # ==================================================
    
    # Session cookie security
    SESSION_COOKIE_HTTPONLY = True              # JavaScript se cookies access nahi hongi
    SESSION_COOKIE_SAMESITE = "Lax"             # CSRF protection me help karta hai
    SESSION_COOKIE_SECURE = False               # ⚠️ Production me TRUE karo (HTTPS ke liye)
    PERMANENT_SESSION_LIFETIME = 60 * 60 * 24 * 7  # 7 days
    
    # CSRF Protection (Flask-WTF)
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600                  # 1 hour (form submit karne ka time)
    WTF_CSRF_SSL_STRICT = False                 # Production me True karo
    
    # Rate Limiting (Flask-Limiter)
    RATELIMIT_STORAGE_URI = "memory://"         # Production me Redis use karo
    RATELIMIT_STRATEGY = "fixed-window"
    RATELIMIT_DEFAULT = "200 per day;50 per hour"
    RATELIMIT_HEADERS_ENABLED = True