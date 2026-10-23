"""
Zenith - Flask E-Commerce Application
+ Cloudinary Integration for permanent image uploads
+ Active/Inactive product separation in admin panel
+ Jinja filter for smart image URL (Cloudinary + local) + auto-optimization
+ Admin products: search + filter + sort + pagination (server-side)
+ Admin orders: search + status filter + sort + pagination (server-side)
+ Admin users: search + role filter + sort + pagination (server-side)
+ Admin dashboard: today/week/month stats + revenue chart + top products + low stock
+ Permanent delete: DB delete + Cloudinary image cleanup
+ Performance: eager loading + image optimization
+ Coupon System: admin CRUD + cart apply + checkout discount + active suggestions
+ Email System: order confirmation + payment receipt + cancel + status + welcome
+ Review System: verified buyer reviews + admin moderation + auto rating update
+ ✅ Frontend Filters: price/size/color/category/sort/stock/sale
+ ✅ SendGrid Integration (Bypasses Render SMTP block)
"""
import warnings

warnings.filterwarnings(
    "ignore",
    message=".*Unable to find acceptable character detection.*"
)

from flask import (
    Flask, render_template, abort, redirect, url_for,
    request, flash, jsonify, session
)

from config import Config
from models import db, User, Order, OrderItem, Product, Coupon, Review, utc_now

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from flask_mail import Mail, Message
from flask_wtf.csrf import CSRFProtect, CSRFError
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename
from sqlalchemy.orm import joinedload

from functools import wraps
import re
import secrets
import json
import os
import uuid
import razorpay
import requests # ✅ NEW: SendGrid API ke liye
from datetime import datetime, timedelta, timezone


# ==================================================
# CLOUDINARY (Optional — fallback to local if not set)
# ==================================================

try:
    import cloudinary
    import cloudinary.uploader

    _cloudinary_url = os.environ.get("CLOUDINARY_URL", "").strip()

    if _cloudinary_url:
        cloudinary.config(cloudinary_url=_cloudinary_url, secure=True)
        CLOUDINARY_ENABLED = True
        print("✅ Cloudinary configured — uploads will go to CDN")
    else:
        CLOUDINARY_ENABLED = False
        print("⚠️  CLOUDINARY_URL not set — falling back to local uploads")

except ImportError:
    cloudinary = None
    CLOUDINARY_ENABLED = False
    print("⚠️  cloudinary package not installed — using local uploads")


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)
app.config.from_object(Config)


# ==================================================
# SECURITY HEADERS
# ==================================================

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# ==================================================
# DATABASE
# ==================================================

db.init_app(app)


# ==================================================
# EMAIL
# ==================================================

mail = Mail(app)


# ==================================================
# SENDGRID API HELPER (Bypasses Render SMTP Block)
# ==================================================

def send_email_via_sendgrid(to_email, subject, html_content):
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("❌ SENDGRID_API_KEY is missing from environment variables!")
        return False

    # ⚠️ IMPORTANT: Yahan apni wo email daalo jo SendGrid pe verify ki hai
    from_email = "shubhamchoudhary9756@gmail.com" 

    url = "https://api.sendgrid.com/v3/mail/send"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "personalizations": [{"to": [{"email": to_email}]}],
        "from": {"email": from_email, "name": "Zenith"},
        "subject": subject,
        "content": [{"type": "text/html", "value": html_content}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 202:
            print(f"✅ Email sent to {to_email} via SendGrid")
            return True
        else:
            print(f"❌ SendGrid Error ({response.status_code}): {response.text}")
            return False
    except Exception as e:
        print(f"❌ SendGrid Request Failed: {e}")
        return False


# ==================================================
# EMAIL SYSTEM (emails.py)
# ==================================================

try:
    from emails import (
        init_email,
        send_order_placed_email,
        send_payment_success_email,
        send_order_cancelled_email,
        send_status_update_email,
        send_welcome_email,
    )
    init_email(mail, app)
    EMAIL_SYSTEM_ENABLED = True
    print("✅ Email system initialized")

except ImportError as e:
    EMAIL_SYSTEM_ENABLED = False
    print(f"⚠️  emails.py not found — email system disabled ({e})")

    def send_order_placed_email(order, user): return False
    def send_payment_success_email(order, user): return False
    def send_order_cancelled_email(order, user): return False
    def send_status_update_email(order, user, old_status, new_status): return False
    def send_welcome_email(user): return False

except Exception as e:
    EMAIL_SYSTEM_ENABLED = False
    print(f"⚠️  Email system init error: {e}")

    def send_order_placed_email(order, user): return False
    def send_payment_success_email(order, user): return False
    def send_order_cancelled_email(order, user): return False
    def send_status_update_email(order, user, old_status, new_status): return False
    def send_welcome_email(user): return False


# ==================================================
# CSRF
# ==================================================

csrf = CSRFProtect(app)


# ==================================================
# RATE LIMITING
# ==================================================

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=app.config.get("RATELIMIT_STORAGE_URI", "memory://")
)


# ==================================================
# RAZORPAY CLIENT
# ==================================================

razorpay_client = razorpay.Client(
    auth=(
        app.config["RAZORPAY_KEY_ID"],
        app.config["RAZORPAY_KEY_SECRET"]
    )
)


# ==================================================
# FILE UPLOAD CONFIG
# ==================================================

UPLOAD_FOLDER = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "static", "images", "uploads"
)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}
ALLOWED_MIME_TYPES = {
    "image/png", "image/jpeg", "image/jpg",
    "image/gif", "image/webp"
}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024


# ==================================================
# FLASK LOGIN
# ==================================================

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please login to continue."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


# ==================================================
# JINJA FILTER — Smart Product Image URL
# ==================================================

@app.template_filter('product_image')
def product_image_filter(image_path):
    if not image_path:
        return url_for('static', filename='images/placeholder.png')

    image_path = str(image_path).strip()

    if "cloudinary.com" in image_path and "/upload/" in image_path:
        parts = image_path.split("/upload/", 1)
        if len(parts) == 2:
            return f"{parts[0]}/upload/q_auto,f_auto,w_800/{parts[1]}"
        return image_path

    if image_path.startswith('http://') or image_path.startswith('https://'):
        return image_path

    return url_for('static', filename=image_path)


# ==================================================
# VALIDATION HELPERS
# ==================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{9,14}$')


def is_valid_email(email):
    if not email or len(email) > 120:
        return False
    return EMAIL_REGEX.match(email) is not None


def is_valid_phone(phone):
    if not phone:
        return False
    clean_phone = re.sub(r'[\s\-]', '', phone)
    return PHONE_REGEX.match(clean_phone) is not None


def is_strong_password(password):
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(password) > 128:
        return False, "Password is too long."
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."
    return True, "Password is strong."


def safe_int(value, default=0):
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def sanitize_string(value, max_length=500):
    if not value:
        return ""
    return str(value).strip()[:max_length]


# ==================================================
# FILE UPLOAD HELPERS
# ==================================================

def allowed_file(filename):
    if not filename or "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in ALLOWED_EXTENSIONS


def _save_to_cloudinary(file):
    if not CLOUDINARY_ENABLED or cloudinary is None:
        return None
    try:
        upload_result = cloudinary.uploader.upload(
            file,
            folder="zenith/products",
            resource_type="image",
            transformation=[{"quality": "auto:good"}, {"fetch_format": "auto"}]
        )
        return upload_result.get("secure_url") or upload_result.get("url")
    except Exception as e:
        print(f"❌ Cloudinary upload error: {e}")
        return None


def _save_locally(file):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in ALLOWED_MIME_TYPES:
            return None

    ext = file.filename.rsplit(".", 1)[1].lower()
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    safe_name = secure_filename(unique_name)
    if not safe_name:
        return None

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], safe_name)
    real_upload = os.path.realpath(app.config["UPLOAD_FOLDER"])
    real_filepath = os.path.realpath(filepath)
    if not real_filepath.startswith(real_upload):
        return None

    file.save(filepath)
    return f"images/uploads/{safe_name}"


def save_uploaded_file(file):
    if not file or not file.filename:
        return None
    if not allowed_file(file.filename):
        return None
    if hasattr(file, 'content_type') and file.content_type:
        if file.content_type not in ALLOWED_MIME_TYPES:
            return None
    if CLOUDINARY_ENABLED:
        url = _save_to_cloudinary(file)
        if url:
            return url
    return _save_locally(file)


def _delete_cloudinary_image(image_url):
    if not image_url:
        return True
    image_url = str(image_url).strip()
    if not image_url.startswith("http://") and not image_url.startswith("https://"):
        return True
    if "cloudinary.com" not in image_url:
        return True
    if not CLOUDINARY_ENABLED or cloudinary is None:
        return True

    try:
        from urllib.parse import urlparse
        import re as _re
        parsed = urlparse(image_url)
        path = parsed.path
        if "/upload/" not in path:
            return True
        after_upload = path.split("/upload/", 1)[1]
        after_upload = _re.sub(r'^[^/]*\/v\d+\/', '', after_upload) if _re.match(r'^[^/]*\/v\d+\/', after_upload) else _re.sub(r'^v\d+/', '', after_upload)
        public_id = _re.sub(r'\.[a-zA-Z0-9]+$', '', after_upload)
        if not public_id:
            return True
        cloudinary.uploader.destroy(public_id, resource_type="image")
        print(f"✅ Cloudinary image deleted: {public_id}")
        return True
    except Exception as e:
        print(f"⚠️  Cloudinary delete failed: {e}")
        return False


# ==================================================
# ADMIN REQUIRED DECORATOR
# ==================================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("You need admin access to view this page.")
            return redirect(url_for("home"))
        return f(*args, **kwargs)
    return decorated_function


# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():
    featured_products_db = Product.query.filter_by(
        category="featured", is_active=True
    ).all()
    best_sellers_db = Product.query.filter_by(
        category="bestseller", is_active=True
    ).all()

    return render_template(
        "index.html",
        featured_products=[p.to_dict() for p in featured_products_db],
        best_sellers=[p.to_dict() for p in best_sellers_db]
    )


# ==================================================
# PRODUCTS LISTING — with Frontend Filters ✅
# ==================================================

@app.route("/products")
def products():
    """
    Products listing with filters:
    - category, type, filter (existing)
    - price_min, price_max
    - sizes (comma-separated: S,M,L)
    - colors (comma-separated: white,black)
    - sort: newest, price_low, price_high, rating, discount, name_asc
    - in_stock=1, on_sale=1
    - q: search query
    """

    # --- Existing params ---
    category = sanitize_string(request.args.get("category", "").lower(), 50)
    ptype = sanitize_string(request.args.get("type", "").lower(), 50)
    filter_by = sanitize_string(request.args.get("filter", "").lower(), 50)
    search_q = sanitize_string(request.args.get("q", ""), 100)

    # --- ✅ NEW filter params ---
    price_min = safe_float(request.args.get("price_min"), 0)
    price_max = safe_float(request.args.get("price_max"), 0)
    sizes_param = sanitize_string(request.args.get("sizes", ""), 255)
    colors_param = sanitize_string(request.args.get("colors", ""), 255)
    sort_param = sanitize_string(request.args.get("sort", ""), 20)
    in_stock = request.args.get("in_stock", "") == "1"
    on_sale = request.args.get("on_sale", "") == "1"

    # Parse comma-separated sizes/colors
    selected_sizes = [s.strip().lower() for s in sizes_param.split(",") if s.strip()]
    selected_colors = [c.strip().lower() for c in colors_param.split(",") if c.strip()]

    # --- Base query ---
    query = Product.query.filter_by(is_active=True)

    # --- Existing filters ---
    if category:
        query = query.filter(db.or_(
            Product.subcategory.ilike(f'%{category}%'),
            Product.name.ilike(f'%{category}%'),
            Product.description.ilike(f'%{category}%')
        ))
    if ptype:
        query = query.filter(db.or_(
            Product.subcategory.ilike(f'%{ptype}%'),
            Product.name.ilike(f'%{ptype}%'),
            Product.description.ilike(f'%{ptype}%')
        ))
    if search_q:
        query = query.filter(db.or_(
            Product.name.ilike(f'%{search_q}%'),
            Product.description.ilike(f'%{search_q}%'),
            Product.subcategory.ilike(f'%{search_q}%'),
            Product.category.ilike(f'%{search_q}%')
        ))

    # --- ✅ NEW: Price range filter ---
    if price_min > 0:
        query = query.filter(Product.price >= price_min)
    if price_max > 0:
        query = query.filter(Product.price <= price_max)

    # --- ✅ NEW: Size filter (OR across selected sizes) ---
    if selected_sizes:
        size_conditions = [
            Product.sizes.ilike(f'%{s}%') for s in selected_sizes
        ]
        query = query.filter(db.or_(*size_conditions))

    # --- ✅ NEW: Color filter (OR across selected colors) ---
    if selected_colors:
        color_conditions = [
            Product.colors.ilike(f'%{c}%') for c in selected_colors
        ]
        query = query.filter(db.or_(*color_conditions))

    # --- ✅ NEW: In-stock filter ---
    if in_stock:
        query = query.filter(Product.stock > 0)

    # --- ✅ NEW: On-sale filter ---
    if on_sale:
        query = query.filter(
            Product.old_price.isnot(None),
            Product.old_price > Product.price
        )

    # --- Existing filter_by (legacy — collection pages) ---
    if filter_by == "new":
        query = query.order_by(Product.id.desc())
    elif filter_by == "bestsellers":
        query = query.order_by(Product.rating.desc())
    elif filter_by == "sale":
        query = query.filter(Product.old_price.isnot(None))
        query = query.filter(Product.old_price > Product.price)
    elif filter_by == "premium":
        query = query.filter(Product.price >= 2000)
    elif filter_by == "under999":
        query = query.filter(Product.price <= 999)
    elif filter_by == "spring":
        query = query.filter(Product.name.ilike('%summer%'))
    elif filter_by == "autumn":
        query = query.filter(Product.name.ilike('%winter%'))
    elif filter_by == "monsoon":
        query = query.filter(Product.name.ilike('%jacket%'))
    elif filter_by == "holiday":
        query = query.filter(Product.name.ilike('%premium%'))

    # --- ✅ NEW: Sort (overrides filter_by default ordering) ---
    if sort_param == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort_param == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort_param == "rating":
        query = query.order_by(Product.rating.desc())
    elif sort_param == "discount":
        query = query.filter(
            Product.old_price.isnot(None),
            Product.old_price > Product.price
        ).order_by((Product.old_price - Product.price).desc())
    elif sort_param == "name_asc":
        query = query.order_by(Product.name.asc())
    elif sort_param == "newest":
        query = query.order_by(Product.created_at.desc())
    elif not filter_by:
        # Only apply default ordering if filter_by wasn't set
        query = query.order_by(Product.created_at.desc())

    all_products = query.all()

    # --- Title mapping ---
    title_map = {
        "new": "New Arrivals", "bestsellers": "Best Sellers",
        "sale": "Sale", "premium": "Premium Edit",
        "under999": "Under ₹999", "spring": "Spring / Summer",
        "autumn": "Autumn / Winter", "monsoon": "Monsoon Edit",
        "holiday": "Holiday Edit",
    }

    if search_q:
        page_title = f'Search: "{search_q}"'
    elif filter_by in title_map:
        page_title = title_map[filter_by]
    elif category:
        page_title = f"{category.title()}'s Collection"
    elif ptype:
        page_title = ptype.title()
    else:
        page_title = "All Products"

    # --- ✅ NEW: Available filter options (from ALL active products) ---
    all_active = Product.query.filter_by(is_active=True).all()

    # Collect unique sizes
    available_sizes_set = set()
    for p in all_active:
        for s in (p.size_list or []):
            available_sizes_set.add(s.upper())

    # Sort sizes smartly: S, M, L, XL, XXL first, then numeric
    size_order = {"S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5, "XXXL": 6}
    available_sizes = sorted(
        available_sizes_set,
        key=lambda x: (size_order.get(x, 99), x)
    )

    # Collect unique colors
    available_colors_set = set()
    for p in all_active:
        for c in (p.color_list or []):
            available_colors_set.add(c.lower())
    available_colors = sorted(available_colors_set)

    # Price range for slider
    price_stats = db.session.query(
        db.func.min(Product.price),
        db.func.max(Product.price)
    ).filter(Product.is_active == True).first()

    price_range = {
        "min": int(price_stats[0] or 0),
        "max": int(price_stats[1] or 5000),
    }

    # --- ✅ NEW: Filter state for template ---
    filter_state = {
        "price_min": price_min,
        "price_max": price_max,
        "sizes": selected_sizes,
        "colors": selected_colors,
        "sort": sort_param,
        "in_stock": in_stock,
        "on_sale": on_sale,
    }

    # --- Active filter count (for badge) ---
    active_filter_count = 0
    if price_min > 0 or price_max > 0: active_filter_count += 1
    if selected_sizes: active_filter_count += 1
    if selected_colors: active_filter_count += 1
    if in_stock: active_filter_count += 1
    if on_sale: active_filter_count += 1
    if search_q: active_filter_count += 1

    return render_template(
        "products.html",
        products=[p.to_dict() for p in all_products],
        page_title=page_title,
        category=category,
        ptype=ptype,
        filter_by=filter_by,
        search_q=search_q,
        available_sizes=available_sizes,
        available_colors=available_colors,
        price_range=price_range,
        filter_state=filter_state,
        active_filter_count=active_filter_count,
        result_count=len(all_products),
    )


# ==================================================
# PRODUCT DETAILS — with reviews ✅
# ==================================================

@app.route("/product/<int:product_id>")
def product(product_id):
    product_db = db.session.get(Product, product_id)
    if product_db is None or not product_db.is_active:
        abort(404)

    # ✅ Fetch approved reviews
    reviews = Review.query.options(
        joinedload(Review.user)
    ).filter_by(
        product_id=product_id,
        is_approved=True
    ).order_by(Review.created_at.desc()).all()

    # ✅ Rating distribution
    rating_distribution = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    total_reviews = len(reviews)
    avg_rating = 0.0

    if reviews:
        for r in reviews:
            if r.rating in rating_distribution:
                rating_distribution[r.rating] += 1
        avg_rating = round(sum(r.rating for r in reviews) / total_reviews, 1)

    # ✅ Check if current user can review
    can_review = False
    user_review = None
    purchase_order = None

    if current_user.is_authenticated:
        user_review = Review.query.filter_by(
            user_id=current_user.id,
            product_id=product_id
        ).first()

        if not user_review:
            purchase_order = db.session.query(Order).join(OrderItem).filter(
                Order.user_id == current_user.id,
                OrderItem.product_id == product_id,
                Order.status.in_(["delivered", "processing", "shipped"])
            ).first()
            can_review = purchase_order is not None

    return render_template(
        "product.html",
        product=product_db.to_dict(),
        reviews=[r.to_dict() for r in reviews],
        review_count=total_reviews,
        avg_rating=avg_rating,
        rating_distribution=rating_distribution,
        can_review=can_review,
        user_review=user_review.to_dict() if user_review else None,
        purchase_order_id=purchase_order.id if purchase_order else None,
    )


# ==================================================
# CUSTOMIZE PRODUCT PAGE
# ==================================================

@app.route("/customize/<int:product_id>")
def customize(product_id):
    product_db = db.session.get(Product, product_id)
    if product_db is None or not product_db.is_active:
        abort(404)
    return render_template("customize.html", product=product_db.to_dict())


# ==================================================
# CART & WISHLIST
# ==================================================

@app.route("/cart")
def cart():
    return render_template("cart.html")


@app.route("/wishlist")
def wishlist():
    return render_template("wishlist.html")


# ==================================================
# SIGNUP — with Welcome Email ✅
# ==================================================

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def signup():
    if request.method == "POST":
        full_name = sanitize_string(request.form.get("full_name", ""), 100)
        email = sanitize_string(request.form.get("email", "").lower(), 120)
        phone = sanitize_string(request.form.get("phone", ""), 20)
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, email, phone, password, confirm_password]):
            flash("All fields are required.")
            return redirect(url_for("signup"))
        if not is_valid_email(email):
            flash("Please enter a valid email address.")
            return redirect(url_for("signup"))
        if not is_valid_phone(phone):
            flash("Please enter a valid phone number.")
            return redirect(url_for("signup"))

        is_strong, message = is_strong_password(password)
        if not is_strong:
            flash(message)
            return redirect(url_for("signup"))
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please login instead.")
            return redirect(url_for("login"))

        new_user = User(
            full_name=full_name, email=email,
            phone=phone, password=generate_password_hash(password)
        )
        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Signup Error: {e}")
            flash("Something went wrong. Please try again.")
            return redirect(url_for("signup"))

        try:
            send_welcome_email(new_user)
        except Exception as e:
            print(f"Welcome email error: {e}")

        flash("Account created successfully! Please login.")
        return redirect(url_for("login"))

    return render_template("signup.html")


# ==================================================
# LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_panel"))
        return redirect(url_for("home"))

    if request.method == "POST":
        email = sanitize_string(request.form.get("email", "").lower(), 120)
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("login"))

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash("Login successful!")
            if user.is_admin:
                return redirect(url_for("admin_panel"))
            return redirect(url_for("home"))

        flash("Invalid email or password.")
        return redirect(url_for("login"))

    return render_template("login.html")


# ==================================================
# ADMIN LOGIN
# ==================================================

@app.route("/admin-login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def admin_login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_panel"))
        return redirect(url_for("home"))

    if request.method == "POST":
        email = sanitize_string(request.form.get("email", "").lower(), 120)
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        if not email or not password:
            flash("Email and password are required.")
            return redirect(url_for("admin_login"))

        user = User.query.filter_by(email=email).first()

        if user and user.is_admin and check_password_hash(user.password, password):
            login_user(user, remember=remember)
            flash("Admin login successful!")
            return redirect(url_for("admin_panel"))

        flash("Invalid admin credentials.")
        return redirect(url_for("admin_login"))

    return render_template("admin_login.html")


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.")
    return redirect(url_for("home"))


# ==================================================
# FORGOT PASSWORD (UPDATED FOR SENDGRID) ✅
# ==================================================

@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = sanitize_string(request.form.get("email", "").lower(), 120)

        if not email:
            flash("Email is required.")
            return redirect(url_for("forgot_password"))

        user = User.query.filter_by(email=email).first()

        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiry = utc_now() + timedelta(hours=1)
            db.session.commit()

            reset_link = url_for("reset_password", token=token, _external=True)

            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #faf8f5;">
                <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #c9a961;">
                    <h1 style="color: #1a1a1a; font-family: Georgia, serif; margin: 0; font-size: 28px; letter-spacing: 3px;">ZENITH</h1>
                    <p style="color: #c9a961; font-size: 12px; letter-spacing: 2px; margin: 5px 0 0 0;">WEAR THE PEAK</p>
                </div>
                <div style="padding: 40px 30px; background: #ffffff;">
                    <h2 style="color: #1a1a1a; font-family: Georgia, serif; font-weight: 500;">Password Reset Request</h2>
                    <p style="color: #555; line-height: 1.7; font-size: 15px;">Hi <strong>{user.full_name}</strong>,</p>
                    <p style="color: #555; line-height: 1.7; font-size: 15px;">We received a request to reset your Zenith account password. Click the button below to create a new password.</p>
                    <div style="text-align: center; margin: 35px 0;">
                        <a href="{reset_link}" style="display: inline-block; padding: 16px 40px; background: #1a1a1a; color: #ffffff; text-decoration: none; letter-spacing: 1.5px; font-size: 13px; text-transform: uppercase; font-weight: 600;">Reset Password</a>
                    </div>
                    <p style="color: #999; font-size: 13px; line-height: 1.7;">This link will expire in <strong>1 hour</strong>.</p>
                </div>
                <div style="text-align: center; padding: 20px 0; color: #999; font-size: 12px;">© 2026 Zenith. All Rights Reserved.</div>
            </div>
            """

            # ✅ Send via SendGrid API
            send_email_via_sendgrid(
                to_email=email,
                subject="Zenith - Password Reset Link",
                html_content=html_content
            )

        flash("If this email is registered, a reset link has been sent.")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# ==================================================
# RESET PASSWORD
# ==================================================

@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):
    if not token or len(token) > 100 or not re.match(r'^[A-Za-z0-9_\-]+$', token):
        flash("Invalid reset link.")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(reset_token=token).first()

    if not user:
        flash("Invalid or expired reset link.")
        return redirect(url_for("forgot_password"))

    now = utc_now()
    expiry = user.reset_token_expiry
    if expiry is not None and expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)

    if not expiry or expiry < now:
        flash("Reset link has expired. Please request a new one.")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("reset_password", token=token))

        is_strong, message = is_strong_password(password)
        if not is_strong:
            flash(message)
            return redirect(url_for("reset_password", token=token))
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("reset_password", token=token))

        user.password = generate_password_hash(password)
        user.reset_token = None
        user.reset_token_expiry = None
        db.session.commit()

        flash("Password reset successful! Please login.")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token)


# ==================================================
# PROFILE
# ==================================================

@app.route("/profile")
@login_required
def profile():
    try:
        if hasattr(current_user.orders, 'count'):
            orders_count = current_user.orders.count()
        else:
            orders_count = len(current_user.orders)
    except Exception as e:
        print(f"Profile orders count error: {e}")
        orders_count = 0

    try:
        reviews_count = Review.query.filter_by(user_id=current_user.id).count()
    except Exception:
        reviews_count = 0

    return render_template(
        "profile.html",
        user=current_user,
        orders_count=orders_count,
        reviews_count=reviews_count,
    )


@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    full_name = sanitize_string(request.form.get("full_name", ""), 100)
    phone = sanitize_string(request.form.get("phone", ""), 20)

    if not full_name or not phone:
        flash("All fields are required.")
        return redirect(url_for("profile"))
    if not is_valid_phone(phone):
        flash("Please enter a valid phone number.")
        return redirect(url_for("profile"))

    current_user.full_name = full_name
    current_user.phone = phone
    db.session.commit()

    flash("Profile updated successfully!")
    return redirect(url_for("profile"))


# ==================================================
# COUPON — VALIDATE (AJAX API)
# ==================================================

@app.route("/api/coupon/validate", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per minute")
def validate_coupon():
    try:
        data = request.get_json(silent=True) or {}
        code = sanitize_string(data.get("code", "").upper(), 50)
        amount = safe_float(data.get("amount", 0))

        if not code:
            return jsonify({"valid": False, "discount": 0, "message": "Please enter a coupon code."})

        if amount <= 0:
            return jsonify({"valid": False, "discount": 0, "message": "Invalid cart amount."})

        coupon = Coupon.query.filter_by(code=code).first()

        if not coupon:
            return jsonify({"valid": False, "discount": 0, "message": "Invalid coupon code."})

        discount, error = coupon.calculate_discount(amount)

        if error:
            return jsonify({"valid": False, "discount": 0, "message": error})

        return jsonify({
            "valid": True,
            "discount": discount,
            "code": coupon.code,
            "message": f"🎉 {coupon.discount_percent}% off applied!",
            "new_total": round(amount - discount, 2)
        })

    except Exception as e:
        print(f"Coupon validate error: {e}")
        return jsonify({"valid": False, "discount": 0, "message": "Something went wrong."}), 500


# ==================================================
# COUPON — LIST ACTIVE
# ==================================================

@app.route("/api/coupon/active", methods=["GET"])
@limiter.limit("60 per minute")
def list_active_coupons():
    try:
        now = utc_now()

        coupons = Coupon.query.filter(
            Coupon.is_active == True
        ).filter(
            db.or_(
                Coupon.expiry_date.is_(None),
                Coupon.expiry_date > now
            )
        ).filter(
            db.or_(
                Coupon.usage_limit.is_(None),
                Coupon.used_count < Coupon.usage_limit
            )
        ).order_by(
            Coupon.discount_percent.desc()
        ).limit(20).all()

        return jsonify({
            "coupons": [
                {
                    "code": c.code,
                    "discount_percent": c.discount_percent,
                    "min_order_amount": float(c.min_order_amount or 0),
                    "max_discount": float(c.max_discount) if c.max_discount else None,
                }
                for c in coupons
            ]
        })

    except Exception as e:
        print(f"List coupons error: {e}")
        return jsonify({"coupons": []}), 200


# ==================================================
# CHECKOUT — with coupon support + order placed email ✅
# ==================================================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        full_name = sanitize_string(request.form.get("full_name", ""), 100)
        address = sanitize_string(request.form.get("address", ""), 300)
        city = sanitize_string(request.form.get("city", ""), 50)
        state = sanitize_string(request.form.get("state", ""), 50)
        pincode = sanitize_string(request.form.get("pincode", ""), 10)
        payment_method = sanitize_string(
            request.form.get("payment_method", "cod").lower(), 20
        )
        coupon_code = sanitize_string(request.form.get("coupon_code", "").upper(), 50)

        if not all([full_name, address, city, state, pincode]):
            flash("All fields are required.")
            return redirect(url_for("checkout"))
        if payment_method not in ["cod", "card", "upi"]:
            flash("Invalid payment method.")
            return redirect(url_for("checkout"))
        if not pincode.isdigit() or len(pincode) != 6:
            flash("Please enter a valid 6-digit pincode.")
            return redirect(url_for("checkout"))

        try:
            cart_data = request.form.get("cart_data", "[]")
            cart_items = json.loads(cart_data)
        except (json.JSONDecodeError, TypeError):
            flash("Invalid cart data.")
            return redirect(url_for("cart"))

        if not isinstance(cart_items, list) or not cart_items:
            flash("Your cart is empty.")
            return redirect(url_for("cart"))
        if len(cart_items) > 50:
            flash("Too many items in cart.")
            return redirect(url_for("cart"))

        validated_items = []
        total_amount = 0.0

        for item in cart_items:
            product_id = safe_int(item.get("id"))
            quantity = safe_int(item.get("quantity"), 0)

            if quantity <= 0 or quantity > 100:
                flash("Invalid quantity.")
                return redirect(url_for("cart"))

            product = db.session.get(Product, product_id)

            if not product or not product.is_active:
                flash("Product not available.")
                return redirect(url_for("cart"))
            if product.stock < quantity:
                flash(f"'{product.name}' sirf {product.stock} available hai.")
                return redirect(url_for("cart"))

            size = sanitize_string(item.get("size", ""), 10) or None
            color = sanitize_string(item.get("color", ""), 30) or None

            subtotal = product.price * quantity
            total_amount += subtotal

            validated_items.append({
                "product": product, "quantity": quantity,
                "size": size, "color": color,
                "price": product.price,
            })

        discount_amount = 0.0
        applied_coupon = None

        if coupon_code:
            coupon = Coupon.query.filter_by(code=coupon_code).first()
            if coupon:
                discount, error = coupon.calculate_discount(total_amount)
                if not error and discount > 0:
                    discount_amount = discount
                    applied_coupon = coupon
                else:
                    flash(f"Coupon: {error}")
                    return redirect(url_for("cart"))
            else:
                flash("Invalid coupon code.")
                return redirect(url_for("cart"))

        final_amount = round(total_amount - discount_amount, 2)
        if final_amount < 0:
            final_amount = 0

        shipping_address = f"{address}, {city}, {state} - {pincode}"

        try:
            order = Order(
                user_id=current_user.id,
                total_amount=final_amount,
                status="pending",
                payment_method=payment_method,
                payment_status="pending",
                shipping_address=shipping_address,
                coupon_code=applied_coupon.code if applied_coupon else None,
                discount_amount=discount_amount
            )
            db.session.add(order)
            db.session.flush()

            for vi in validated_items:
                p = vi["product"]
                db.session.add(OrderItem(
                    order_id=order.id, product_id=p.id,
                    product_name=p.name, price=vi["price"],
                    quantity=vi["quantity"], size=vi["size"],
                    color=vi["color"]
                ))
                p.stock -= vi["quantity"]

            if applied_coupon:
                applied_coupon.used_count = (applied_coupon.used_count or 0) + 1

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"Checkout Error: {e}")
            flash("Failed to place order. Please try again.")
            return redirect(url_for("checkout"))

        if payment_method == "cod":
            try:
                send_order_placed_email(order, current_user)
            except Exception as e:
                print(f"Order placed email error: {e}")

        if payment_method in ["card", "upi"]:
            return redirect(url_for("payment_page", order_id=order.id))

        flash("Order placed successfully!")
        return redirect(url_for("order_success", order_id=order.id))

    return render_template("checkout.html")


# ==================================================
# PAYMENT ROUTES
# ==================================================

@app.route("/payment/<int:order_id>")
@login_required
def payment_page(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    if order.payment_status == "paid":
        flash("This order is already paid.")
        return redirect(url_for("order_success", order_id=order.id))
    return render_template("payment.html", order=order, razorpay_key_id=app.config["RAZORPAY_KEY_ID"])


@app.route("/payment/create-order", methods=["POST"])
@login_required
@csrf.exempt
@limiter.limit("20 per minute")
def create_payment_order():
    try:
        data = request.get_json(silent=True) or {}
        order_id = safe_int(data.get("order_id"))

        if order_id <= 0:
            return jsonify({"error": "Invalid order"}), 400

        order = db.session.get(Order, order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404
        if order.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        if order.payment_status == "paid":
            return jsonify({"error": "Already paid"}), 400

        amount_paise = int(round(order.total_amount * 100))

        if amount_paise <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        razorpay_order = razorpay_client.order.create({
            "amount": amount_paise, "currency": "INR",
            "receipt": f"receipt_{order.id}", "payment_capture": 1
        })

        order.razorpay_order_id = razorpay_order["id"]
        db.session.commit()

        return jsonify({
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": app.config["RAZORPAY_KEY_ID"],
            "db_order_id": order.id
        })
    except Exception as e:
        print(f"Razorpay Error: {e}")
        return jsonify({"error": "Payment initialization failed"}), 500


@app.route("/payment/verify", methods=["POST"])
@login_required
@csrf.exempt
@limiter.limit("20 per minute")
def verify_payment():
    try:
        data = request.get_json(silent=True) or {}
        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        order_id = safe_int(data.get("order_id"))

        if not all([razorpay_payment_id, razorpay_order_id, razorpay_signature]):
            return jsonify({"error": "Missing payment data"}), 400

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        order = db.session.get(Order, order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404
        if order.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        if order.razorpay_order_id != razorpay_order_id:
            return jsonify({"error": "Order mismatch"}), 400
        if order.payment_status == "paid":
            return jsonify({"status": "success", "already_paid": True})

        order.payment_id = razorpay_payment_id
        order.payment_status = "paid"
        order.status = "processing"
        db.session.commit()

        try:
            send_payment_success_email(order, current_user)
        except Exception as e:
            print(f"Payment success email error: {e}")

        return jsonify({"status": "success", "payment_id": razorpay_payment_id})

    except razorpay.errors.SignatureVerificationError:
        db.session.rollback()
        return jsonify({"status": "failed", "error": "Signature verification failed"}), 400
    except Exception as e:
        db.session.rollback()
        print(f"Payment Verify Error: {e}")
        return jsonify({"status": "failed", "error": "Verification failed"}), 500


@app.route("/payment/failed/<int:order_id>", methods=["POST"])
@login_required
@csrf.exempt
@limiter.limit("20 per minute")
def payment_failed(order_id):
    try:
        order = db.session.get(Order, order_id)
        if not order:
            return jsonify({"error": "Order not found"}), 404
        if order.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403
        if order.payment_status == "paid":
            return jsonify({"status": "already_paid"}), 200
        if order.status == "cancelled":
            return jsonify({"status": "already_cancelled"}), 200

        for item in order.items:
            product = db.session.get(Product, item.product_id)
            if product:
                product.stock += item.quantity

        order.status = "cancelled"
        order.payment_status = "failed"
        db.session.commit()
        return jsonify({"status": "cancelled"}), 200
    except Exception as e:
        db.session.rollback()
        print(f"Payment Failed Handler Error: {e}")
        return jsonify({"error": "Failed to process"}), 500


@app.route("/payment-success/<int:order_id>")
@login_required
def payment_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("payment_success.html", order=order)


@app.route("/payment-failure/<int:order_id>")
@login_required
def payment_failure(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("payment_failure.html", order=order)


@app.route("/order-success/<int:order_id>")
@login_required
def order_success(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("order_success.html", order=order)


# ==================================================
# ORDERS (User side)
# ==================================================

@app.route("/orders")
@login_required
def orders():
    user_orders = Order.query.options(
        joinedload(Order.items)
    ).filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template("orders.html", orders=user_orders)


@app.route("/order/<int:order_id>/cancel", methods=["POST"])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    if order.status not in ["pending", "processing"]:
        flash("Order cannot be cancelled at this stage.")
        return redirect(url_for("orders"))

    try:
        for item in order.items:
            product = db.session.get(Product, item.product_id)
            if product:
                product.stock += item.quantity
        order.status = "cancelled"
        db.session.commit()

        try:
            send_order_cancelled_email(order, current_user)
        except Exception as e:
            print(f"Cancel email error: {e}")

    except Exception as e:
        db.session.rollback()
        print(f"Cancel Error: {e}")
        flash("Failed to cancel order.")
        return redirect(url_for("orders"))

    flash("Order cancelled successfully.")
    return redirect(url_for("orders"))


@app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("order_details.html", order=order)


# ==================================================
# REVIEWS — USER ROUTES
# ==================================================

@app.route("/product/<int:product_id>/review", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def submit_review(product_id):
    """Submit a new review for a product"""

    product_db = db.session.get(Product, product_id)
    if not product_db or not product_db.is_active:
        abort(404)

    existing = Review.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()

    if existing:
        flash("You've already reviewed this product.")
        return redirect(url_for("product", product_id=product_id))

    purchase_order = db.session.query(Order).join(OrderItem).filter(
        Order.user_id == current_user.id,
        OrderItem.product_id == product_id,
        Order.status.in_(["delivered", "processing", "shipped"])
    ).first()

    if not purchase_order:
        flash("Only verified buyers can review this product.")
        return redirect(url_for("product", product_id=product_id))

    rating = safe_int(request.form.get("rating"), 0)
    title = sanitize_string(request.form.get("title", ""), 150)
    comment = sanitize_string(request.form.get("comment", ""), 2000)
    order_id = safe_int(request.form.get("order_id")) or None

    if rating < 1 or rating > 5:
        flash("Please select a rating between 1 and 5 stars.")
        return redirect(url_for("product", product_id=product_id))

    if not comment or len(comment) < 10:
        flash("Please write at least 10 characters in your review.")
        return redirect(url_for("product", product_id=product_id))

    photo_url = None
    photo_file = request.files.get("photo")
    if photo_file and photo_file.filename:
        photo_url = save_uploaded_file(photo_file)

    try:
        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            order_id=order_id,
            rating=rating,
            title=title or None,
            comment=comment,
            photo_url=photo_url,
            is_approved=False,
            is_verified_purchase=True,
        )
        db.session.add(review)
        db.session.commit()

        flash("Thank you! Your review has been submitted and will appear after admin approval. ⭐")
        return redirect(url_for("product", product_id=product_id))

    except Exception as e:
        db.session.rollback()
        print(f"Review submit error: {e}")
        flash("Failed to submit review. Please try again.")
        return redirect(url_for("product", product_id=product_id))


@app.route("/review/<int:review_id>/update", methods=["POST"])
@login_required
@limiter.limit("5 per hour")
def update_review(review_id):
    """Update user's own review"""
    review = Review.query.get_or_404(review_id)

    if review.user_id != current_user.id:
        abort(403)

    rating = safe_int(request.form.get("rating"), 0)
    title = sanitize_string(request.form.get("title", ""), 150)
    comment = sanitize_string(request.form.get("comment", ""), 2000)

    if rating < 1 or rating > 5:
        flash("Please select a valid rating.")
        return redirect(url_for("product", product_id=review.product_id))

    if not comment or len(comment) < 10:
        flash("Review must be at least 10 characters.")
        return redirect(url_for("product", product_id=review.product_id))

    try:
        review.rating = rating
        review.title = title or None
        review.comment = comment
        review.is_approved = False
        db.session.commit()

        flash("Review updated! It will re-appear after admin approval.")
    except Exception as e:
        db.session.rollback()
        print(f"Review update error: {e}")
        flash("Failed to update review.")

    return redirect(url_for("product", product_id=review.product_id))


@app.route("/review/<int:review_id>/delete", methods=["POST"])
@login_required
def delete_review(review_id):
    """Delete user's own review"""
    review = Review.query.get_or_404(review_id)

    if review.user_id != current_user.id:
        abort(403)

    product_id = review.product_id

    try:
        db.session.delete(review)
        db.session.commit()
        _update_product_rating(product_id)
        flash("Review deleted.")
    except Exception as e:
        db.session.rollback()
        print(f"Review delete error: {e}")
        flash("Failed to delete review.")

    return redirect(url_for("product", product_id=product_id))


@app.route("/review/<int:review_id>/helpful", methods=["POST"])
@login_required
@csrf.exempt
@limiter.limit("30 per hour")
def mark_review_helpful(review_id):
    """Mark review as helpful (AJAX)"""
    review = Review.query.get_or_404(review_id)

    try:
        review.helpful_count = (review.helpful_count or 0) + 1
        db.session.commit()
        return jsonify({"success": True, "count": review.helpful_count})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False}), 500


def _update_product_rating(product_id):
    """Recalculate & update Product.rating from approved reviews"""
    try:
        product = db.session.get(Product, product_id)
        if not product:
            return

        avg = db.session.query(db.func.avg(Review.rating)).filter(
            Review.product_id == product_id,
            Review.is_approved == True
        ).scalar()

        product.rating = round(float(avg), 1) if avg else 4.5
        db.session.commit()
        print(f"✅ Product #{product_id} rating updated to {product.rating}")

    except Exception as e:
        db.session.rollback()
        print(f"Update product rating error: {e}")


# ==================================================
# ADMIN — DASHBOARD
# ==================================================

@app.route("/admin")
@app.route("/admin/")
@login_required
@admin_required
def admin_panel():
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total_orders = Order.query.count()
    total_users = User.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    pending_orders = Order.query.filter_by(status="pending").count()
    total_products = Product.query.count()

    today_orders = Order.query.filter(Order.created_at >= today_start).count()
    today_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.created_at >= today_start).scalar() or 0
    today_users = User.query.filter(User.created_at >= today_start).count()

    week_orders = Order.query.filter(Order.created_at >= week_start).count()
    week_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.created_at >= week_start).scalar() or 0

    month_orders = Order.query.filter(Order.created_at >= month_start).count()
    month_revenue = db.session.query(db.func.sum(Order.total_amount)).filter(Order.created_at >= month_start).scalar() or 0

    order_status_breakdown = {
        "pending": Order.query.filter_by(status="pending").count(),
        "processing": Order.query.filter_by(status="processing").count(),
        "shipped": Order.query.filter_by(status="shipped").count(),
        "delivered": Order.query.filter_by(status="delivered").count(),
        "cancelled": Order.query.filter_by(status="cancelled").count(),
    }

    revenue_chart_labels = []
    revenue_chart_data = []
    for i in range(6, -1, -1):
        day_start = today_start - timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        day_rev = db.session.query(db.func.sum(Order.total_amount)).filter(
            Order.created_at >= day_start, Order.created_at < day_end
        ).scalar() or 0
        revenue_chart_labels.append(day_start.strftime("%d %b"))
        revenue_chart_data.append(float(day_rev))

    top_products_query = (
        db.session.query(
            OrderItem.product_name,
            db.func.sum(OrderItem.quantity).label("total_qty"),
            db.func.sum(OrderItem.quantity * OrderItem.price).label("total_revenue")
        )
        .group_by(OrderItem.product_name)
        .order_by(db.func.sum(OrderItem.quantity).desc())
        .limit(5).all()
    )
    top_products = [
        {"name": r.product_name, "qty": int(r.total_qty or 0), "revenue": float(r.total_revenue or 0)}
        for r in top_products_query
    ]

    low_stock_products = Product.query.filter(
        Product.is_active == True, Product.stock < 10
    ).order_by(Product.stock.asc()).limit(8).all()

    recent_orders = Order.query.options(joinedload(Order.user)).order_by(Order.created_at.desc()).limit(5).all()
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()

    try:
        pending_reviews_count = Review.query.filter_by(is_approved=False).count()
    except Exception:
        pending_reviews_count = 0

    return render_template(
        "admin_panel.html", active_tab="dashboard",
        total_orders=total_orders, total_users=total_users,
        total_revenue=total_revenue, pending_orders=pending_orders,
        total_products=total_products,
        today_orders=today_orders, today_revenue=today_revenue, today_users=today_users,
        week_orders=week_orders, week_revenue=week_revenue,
        month_orders=month_orders, month_revenue=month_revenue,
        order_status_breakdown=order_status_breakdown,
        revenue_chart_labels=revenue_chart_labels, revenue_chart_data=revenue_chart_data,
        top_products=top_products, low_stock_products=low_stock_products,
        recent_orders=recent_orders, recent_users=recent_users,
        pending_reviews_count=pending_reviews_count,
    )


# ==================================================
# ADMIN — ORDERS
# ==================================================

@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders_tab():
    search_q = sanitize_string(request.args.get("q", ""), 100)
    status_filter = sanitize_string(request.args.get("status", ""), 20)
    sort_by = sanitize_string(request.args.get("sort", "newest"), 20)
    page = max(1, safe_int(request.args.get("page"), 1))
    per_page = 20

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if status_filter and status_filter not in valid_statuses:
        status_filter = ""

    query = Order.query.options(joinedload(Order.user))

    if search_q:
        conditions = [
            User.full_name.ilike(f'%{search_q}%'),
            User.email.ilike(f'%{search_q}%'),
        ]
        try:
            oid = int(search_q)
            conditions.append(Order.id == oid)
        except (ValueError, TypeError):
            pass
        query = query.join(User, Order.user_id == User.id).filter(db.or_(*conditions))

    if status_filter:
        query = query.filter(Order.status == status_filter)

    if sort_by == "amount_high":
        query = query.order_by(Order.total_amount.desc())
    elif sort_by == "amount_low":
        query = query.order_by(Order.total_amount.asc())
    elif sort_by == "oldest":
        query = query.order_by(Order.created_at.asc())
    else:
        sort_by = "newest"
        query = query.order_by(Order.created_at.desc())

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    orders_page = query.offset(offset).limit(per_page).all()

    status_counts = {
        "all": Order.query.count(),
        "pending": Order.query.filter_by(status="pending").count(),
        "processing": Order.query.filter_by(status="processing").count(),
        "shipped": Order.query.filter_by(status="shipped").count(),
        "delivered": Order.query.filter_by(status="delivered").count(),
        "cancelled": Order.query.filter_by(status="cancelled").count(),
    }

    return render_template(
        "admin_panel.html", active_tab="orders",
        orders=orders_page, search_q=search_q,
        status_filter=status_filter, sort_by=sort_by,
        current_page=page, total_pages=total_pages,
        total_count=total_count, per_page=per_page,
        status_counts=status_counts, valid_statuses=valid_statuses,
    )


# ==================================================
# ADMIN — PRODUCTS
# ==================================================

@app.route("/admin/products")
@login_required
@admin_required
def admin_products_tab():
    search_q = sanitize_string(request.args.get("q", ""), 100)
    category_filter = sanitize_string(request.args.get("category", ""), 20)
    sort_by = sanitize_string(request.args.get("sort", "newest"), 20)
    tab = sanitize_string(request.args.get("tab", "active"), 20)
    page = max(1, safe_int(request.args.get("page"), 1))
    per_page = 12

    if tab not in ("active", "deleted"):
        tab = "active"

    is_active_filter = (tab == "active")
    query = Product.query.filter_by(is_active=is_active_filter)

    if search_q:
        query = query.filter(db.or_(
            Product.name.ilike(f'%{search_q}%'),
            Product.description.ilike(f'%{search_q}%'),
            Product.subcategory.ilike(f'%{search_q}%'),
        ))
    if category_filter in ["featured", "bestseller"]:
        query = query.filter(Product.category == category_filter)

    if sort_by == "price_low":
        query = query.order_by(Product.price.asc())
    elif sort_by == "price_high":
        query = query.order_by(Product.price.desc())
    elif sort_by == "name_asc":
        query = query.order_by(Product.name.asc())
    elif sort_by == "stock_low":
        query = query.order_by(Product.stock.asc())
    else:
        sort_by = "newest"
        query = query.order_by(Product.created_at.desc())

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    products_page = query.offset(offset).limit(per_page).all()

    active_count = Product.query.filter_by(is_active=True).count()
    deleted_count = Product.query.filter_by(is_active=False).count()

    return render_template(
        "admin_panel.html", active_tab="products",
        products=products_page,
        active_products=products_page if is_active_filter else [],
        inactive_products=products_page if not is_active_filter else [],
        current_tab=tab, active_count=active_count, deleted_count=deleted_count,
        search_q=search_q, category_filter=category_filter, sort_by=sort_by,
        current_page=page, total_pages=total_pages,
        total_count=total_count, per_page=per_page,
    )


# ==================================================
# ADMIN — USERS
# ==================================================

@app.route("/admin/users")
@login_required
@admin_required
def admin_users_tab():
    search_q = sanitize_string(request.args.get("q", ""), 100)
    role_filter = sanitize_string(request.args.get("role", ""), 20)
    sort_by = sanitize_string(request.args.get("sort", "newest"), 20)
    page = max(1, safe_int(request.args.get("page"), 1))
    per_page = 20

    query = User.query
    if search_q:
        query = query.filter(db.or_(
            User.full_name.ilike(f'%{search_q}%'),
            User.email.ilike(f'%{search_q}%'),
            User.phone.ilike(f'%{search_q}%'),
        ))

    if role_filter == "admin":
        query = query.filter(User.is_admin == True)
    elif role_filter == "user":
        query = query.filter(User.is_admin == False)

    if sort_by == "oldest":
        query = query.order_by(User.created_at.asc())
    elif sort_by == "name_asc":
        query = query.order_by(User.full_name.asc())
    elif sort_by == "name_desc":
        query = query.order_by(User.full_name.desc())
    else:
        sort_by = "newest"
        query = query.order_by(User.created_at.desc())

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    users_page = query.offset(offset).limit(per_page).all()

    total_users_all = User.query.count()
    admin_count = User.query.filter_by(is_admin=True).count()
    regular_count = User.query.filter_by(is_admin=False).count()

    user_ids = [u.id for u in users_page]
    order_counts = {}
    if user_ids:
        rows = db.session.query(Order.user_id, db.func.count(Order.id)).filter(
            Order.user_id.in_(user_ids)
        ).group_by(Order.user_id).all()
        order_counts = {uid: cnt for uid, cnt in rows}

    return render_template(
        "admin_panel.html", active_tab="users",
        users=users_page, search_q=search_q,
        role_filter=role_filter, sort_by=sort_by,
        current_page=page, total_pages=total_pages,
        total_count=total_count, per_page=per_page,
        total_users_all=total_users_all,
        admin_count=admin_count, regular_count=regular_count,
        order_counts=order_counts,
    )


# ==================================================
# ADMIN — COUPONS
# ==================================================

@app.route("/admin/coupons")
@login_required
@admin_required
def admin_coupons_tab():
    search_q = sanitize_string(request.args.get("q", ""), 50)
    status_filter = sanitize_string(request.args.get("status", ""), 20)
    sort_by = sanitize_string(request.args.get("sort", "newest"), 20)
    page = max(1, safe_int(request.args.get("page"), 1))
    per_page = 20

    query = Coupon.query

    if search_q:
        query = query.filter(Coupon.code.ilike(f'%{search_q}%'))

    if status_filter == "active":
        query = query.filter(Coupon.is_active == True)
    elif status_filter == "inactive":
        query = query.filter(Coupon.is_active == False)
    elif status_filter == "expired":
        now = utc_now()
        query = query.filter(Coupon.expiry_date.isnot(None), Coupon.expiry_date < now)
    elif status_filter == "exhausted":
        query = query.filter(
            Coupon.usage_limit.isnot(None),
            Coupon.used_count >= Coupon.usage_limit
        )

    if sort_by == "oldest":
        query = query.order_by(Coupon.created_at.asc())
    elif sort_by == "code_asc":
        query = query.order_by(Coupon.code.asc())
    elif sort_by == "discount_high":
        query = query.order_by(Coupon.discount_percent.desc())
    elif sort_by == "usage_high":
        query = query.order_by(Coupon.used_count.desc())
    else:
        sort_by = "newest"
        query = query.order_by(Coupon.created_at.desc())

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    coupons_page = query.offset(offset).limit(per_page).all()

    now = utc_now()
    total_all = Coupon.query.count()
    active_count = Coupon.query.filter_by(is_active=True).count()
    inactive_count = Coupon.query.filter_by(is_active=False).count()
    expired_count = Coupon.query.filter(
        Coupon.expiry_date.isnot(None), Coupon.expiry_date < now
    ).count()

    return render_template(
        "admin_panel.html", active_tab="coupons",
        coupons=coupons_page, search_q=search_q,
        status_filter=status_filter, sort_by=sort_by,
        current_page=page, total_pages=total_pages,
        total_count=total_count, per_page=per_page,
        total_all=total_all,
        active_count=active_count,
        inactive_count=inactive_count,
        expired_count=expired_count,
    )


@app.route("/admin/coupons/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_coupon():
    if request.method == "POST":
        code = sanitize_string(request.form.get("code", "").upper(), 50)
        discount_percent = safe_int(request.form.get("discount_percent"), 0)
        min_order_amount = safe_float(request.form.get("min_order_amount"), 0)
        max_discount = safe_float(request.form.get("max_discount"), 0)
        usage_limit = safe_int(request.form.get("usage_limit"), 0)
        expiry_str = sanitize_string(request.form.get("expiry_date", ""), 20)
        is_active = request.form.get("is_active") == "on"

        if not code or len(code) < 3:
            flash("Coupon code must be at least 3 characters.")
            return redirect(url_for("admin_add_coupon"))

        if discount_percent < 1 or discount_percent > 100:
            flash("Discount must be between 1% and 100%.")
            return redirect(url_for("admin_add_coupon"))

        existing = Coupon.query.filter_by(code=code).first()
        if existing:
            flash(f"Coupon '{code}' already exists.")
            return redirect(url_for("admin_add_coupon"))

        expiry_date = None
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                flash("Invalid expiry date format.")
                return redirect(url_for("admin_add_coupon"))

        try:
            new_coupon = Coupon(
                code=code,
                discount_percent=discount_percent,
                min_order_amount=min_order_amount,
                max_discount=max_discount if max_discount > 0 else None,
                usage_limit=usage_limit if usage_limit > 0 else None,
                expiry_date=expiry_date,
                is_active=is_active,
                used_count=0
            )
            db.session.add(new_coupon)
            db.session.commit()
            flash(f"Coupon '{code}' created successfully! 🎉")
        except Exception as e:
            db.session.rollback()
            print(f"Add Coupon Error: {e}")
            flash("Failed to create coupon.")

        return redirect(url_for("admin_coupons_tab"))

    return render_template("admin_coupon_form.html", coupon=None, mode="add")


@app.route("/admin/coupons/edit/<int:coupon_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)

    if request.method == "POST":
        code = sanitize_string(request.form.get("code", "").upper(), 50)
        discount_percent = safe_int(request.form.get("discount_percent"), 0)
        min_order_amount = safe_float(request.form.get("min_order_amount"), 0)
        max_discount = safe_float(request.form.get("max_discount"), 0)
        usage_limit = safe_int(request.form.get("usage_limit"), 0)
        expiry_str = sanitize_string(request.form.get("expiry_date", ""), 20)
        is_active = request.form.get("is_active") == "on"

        if not code or len(code) < 3:
            flash("Coupon code must be at least 3 characters.")
            return redirect(url_for("admin_edit_coupon", coupon_id=coupon_id))

        if discount_percent < 1 or discount_percent > 100:
            flash("Discount must be between 1% and 100%.")
            return redirect(url_for("admin_edit_coupon", coupon_id=coupon_id))

        existing = Coupon.query.filter(Coupon.code == code, Coupon.id != coupon_id).first()
        if existing:
            flash(f"Coupon '{code}' already exists.")
            return redirect(url_for("admin_edit_coupon", coupon_id=coupon_id))

        expiry_date = None
        if expiry_str:
            try:
                expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d").replace(
                    hour=23, minute=59, second=59, tzinfo=timezone.utc
                )
            except ValueError:
                flash("Invalid expiry date format.")
                return redirect(url_for("admin_edit_coupon", coupon_id=coupon_id))

        try:
            coupon.code = code
            coupon.discount_percent = discount_percent
            coupon.min_order_amount = min_order_amount
            coupon.max_discount = max_discount if max_discount > 0 else None
            coupon.usage_limit = usage_limit if usage_limit > 0 else None
            coupon.expiry_date = expiry_date
            coupon.is_active = is_active

            db.session.commit()
            flash(f"Coupon '{code}' updated successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Edit Coupon Error: {e}")
            flash("Failed to update coupon.")

        return redirect(url_for("admin_coupons_tab"))

    return render_template("admin_coupon_form.html", coupon=coupon, mode="edit")


@app.route("/admin/coupons/delete/<int:coupon_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)
    code = coupon.code

    try:
        db.session.delete(coupon)
        db.session.commit()
        flash(f"Coupon '{code}' deleted successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Delete Coupon Error: {e}")
        flash("Failed to delete coupon.")

    return redirect(url_for("admin_coupons_tab"))


@app.route("/admin/coupons/toggle/<int:coupon_id>", methods=["POST"])
@login_required
@admin_required
def admin_toggle_coupon(coupon_id):
    coupon = Coupon.query.get_or_404(coupon_id)

    try:
        coupon.is_active = not coupon.is_active
        db.session.commit()
        status = "activated" if coupon.is_active else "deactivated"
        flash(f"Coupon '{coupon.code}' {status}.")
    except Exception as e:
        db.session.rollback()
        print(f"Toggle Coupon Error: {e}")
        flash("Failed to toggle coupon.")

    return redirect(url_for("admin_coupons_tab"))


# ==================================================
# ADMIN — REVIEWS
# ==================================================

@app.route("/admin/reviews")
@login_required
@admin_required
def admin_reviews_tab():
    search_q = sanitize_string(request.args.get("q", ""), 100)
    status_filter = sanitize_string(request.args.get("status", "pending"), 20)
    rating_filter = safe_int(request.args.get("rating"), 0)
    sort_by = sanitize_string(request.args.get("sort", "newest"), 20)
    page = max(1, safe_int(request.args.get("page"), 1))
    per_page = 20

    query = Review.query.options(
        joinedload(Review.user),
        joinedload(Review.product)
    )

    if search_q:
        query = query.join(User, Review.user_id == User.id).filter(db.or_(
            User.full_name.ilike(f'%{search_q}%'),
            User.email.ilike(f'%{search_q}%'),
            Review.comment.ilike(f'%{search_q}%'),
            Review.title.ilike(f'%{search_q}%'),
        ))

    if status_filter == "pending":
        query = query.filter(Review.is_approved == False)
    elif status_filter == "approved":
        query = query.filter(Review.is_approved == True)

    if rating_filter and 1 <= rating_filter <= 5:
        query = query.filter(Review.rating == rating_filter)

    if sort_by == "oldest":
        query = query.order_by(Review.created_at.asc())
    elif sort_by == "rating_high":
        query = query.order_by(Review.rating.desc())
    elif sort_by == "rating_low":
        query = query.order_by(Review.rating.asc())
    else:
        sort_by = "newest"
        query = query.order_by(Review.created_at.desc())

    total_count = query.count()
    total_pages = max(1, (total_count + per_page - 1) // per_page)
    page = min(page, total_pages)
    offset = (page - 1) * per_page
    reviews_page = query.offset(offset).limit(per_page).all()

    total_all = Review.query.count()
    pending_count = Review.query.filter_by(is_approved=False).count()
    approved_count = Review.query.filter_by(is_approved=True).count()
    avg_all = db.session.query(db.func.avg(Review.rating)).scalar() or 0

    return render_template(
        "admin_panel.html",
        active_tab="reviews",
        reviews=reviews_page,
        search_q=search_q,
        status_filter=status_filter,
        rating_filter=rating_filter,
        sort_by=sort_by,
        current_page=page,
        total_pages=total_pages,
        total_count=total_count,
        per_page=per_page,
        total_all=total_all,
        pending_count=pending_count,
        approved_count=approved_count,
        avg_all=round(float(avg_all), 1),
    )


@app.route("/admin/reviews/<int:review_id>/approve", methods=["POST"])
@login_required
@admin_required
def admin_approve_review(review_id):
    review = Review.query.get_or_404(review_id)

    try:
        review.is_approved = True
        db.session.commit()
        _update_product_rating(review.product_id)
        flash(f"Review approved! ⭐ {review.rating}★")
    except Exception as e:
        db.session.rollback()
        print(f"Approve review error: {e}")
        flash("Failed to approve review.")

    return redirect(url_for("admin_reviews_tab", status="approved"))


@app.route("/admin/reviews/<int:review_id>/reject", methods=["POST"])
@login_required
@admin_required
def admin_reject_review(review_id):
    review = Review.query.get_or_404(review_id)
    product_id = review.product_id

    try:
        db.session.delete(review)
        db.session.commit()
        _update_product_rating(product_id)
        flash("Review rejected and removed.")
    except Exception as e:
        db.session.rollback()
        print(f"Reject review error: {e}")
        flash("Failed to reject review.")

    return redirect(url_for("admin_reviews_tab", status="pending"))


@app.route("/admin/reviews/<int:review_id>/delete", methods=["POST"])
@login_required
@admin_required
def admin_delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    product_id = review.product_id

    try:
        db.session.delete(review)
        db.session.commit()
        _update_product_rating(product_id)
        flash("Review deleted permanently.")
    except Exception as e:
        db.session.rollback()
        print(f"Delete review error: {e}")
        flash("Failed to delete review.")

    return redirect(url_for("admin_reviews_tab"))


# ==================================================
# ADMIN — PRODUCT MANAGEMENT
# ==================================================

@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():
    if request.method == "POST":
        name = sanitize_string(request.form.get("name", ""), 200)
        price = safe_float(request.form.get("price"))
        old_price = safe_float(request.form.get("old_price"))
        rating = safe_float(request.form.get("rating"), 4.5)
        description = sanitize_string(request.form.get("description", ""), 2000)
        category = sanitize_string(request.form.get("category", "featured"), 20)
        subcategory = sanitize_string(request.form.get("subcategory", "").lower(), 100)
        stock = safe_int(request.form.get("stock"), 10)

        # ✅ NEW: sizes + colors + brand
        sizes = sanitize_string(request.form.get("sizes", ""), 255)
        colors = sanitize_string(request.form.get("colors", ""), 255)
        brand = sanitize_string(request.form.get("brand", "Zenith"), 100)

        image = save_uploaded_file(request.files.get("image_file")) or sanitize_string(request.form.get("image", ""), 500)
        image2 = save_uploaded_file(request.files.get("image2_file")) or sanitize_string(request.form.get("image2", ""), 500)
        image3 = save_uploaded_file(request.files.get("image3_file")) or sanitize_string(request.form.get("image3", ""), 500)
        image4 = save_uploaded_file(request.files.get("image4_file")) or sanitize_string(request.form.get("image4", ""), 500)

        if not name or price <= 0 or not image:
            flash("Name, Price (> 0), and Image are required.")
            return redirect(url_for("admin_add_product"))
        if category not in ["featured", "bestseller"]:
            flash("Invalid category.")
            return redirect(url_for("admin_add_product"))

        try:
            new_product = Product(
                name=name, price=price,
                old_price=old_price if old_price > 0 else None,
                image=image, image2=image2 or None,
                image3=image3 or None, image4=image4 or None,
                rating=rating if 0 <= rating <= 5 else 4.5,
                description=description, category=category,
                subcategory=subcategory, stock=max(0, stock),
                sizes=sizes, colors=colors, brand=brand or "Zenith",
                is_active=True
            )
            db.session.add(new_product)
            db.session.commit()
            flash(f"Product '{name}' added successfully!")
            return redirect(url_for("admin_products_tab"))
        except Exception as e:
            db.session.rollback()
            print(f"Add Product Error: {e}")
            flash("Failed to add product.")
            return redirect(url_for("admin_add_product"))

    return render_template("admin_product_form.html", product=None, mode="add")


@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        name = sanitize_string(request.form.get("name", ""), 200)
        price = safe_float(request.form.get("price"))
        old_price = safe_float(request.form.get("old_price"))

        if not name or price <= 0:
            flash("Name and Price (> 0) are required.")
            return redirect(url_for("admin_edit_product", product_id=product_id))

        try:
            product.name = name
            product.price = price
            product.old_price = old_price if old_price > 0 else None
            product.rating = safe_float(request.form.get("rating"), 4.5)
            product.description = sanitize_string(request.form.get("description", ""), 2000)
            product.category = sanitize_string(request.form.get("category", "featured"), 20)
            product.subcategory = sanitize_string(request.form.get("subcategory", "").lower(), 100)
            product.stock = max(0, safe_int(request.form.get("stock"), 10))

            # ✅ NEW: sizes + colors + brand
            product.sizes = sanitize_string(request.form.get("sizes", ""), 255)
            product.colors = sanitize_string(request.form.get("colors", ""), 255)
            product.brand = sanitize_string(request.form.get("brand", "Zenith"), 100) or "Zenith"

            for field in ["image", "image2", "image3", "image4"]:
                uploaded = request.files.get(f"{field}_file")
                new_path = save_uploaded_file(uploaded)
                if new_path:
                    setattr(product, field, new_path)
                else:
                    text_val = sanitize_string(request.form.get(field, ""), 500)
                    if text_val:
                        setattr(product, field, text_val)

            db.session.commit()
            flash(f"Product '{product.name}' updated successfully!")
            return redirect(url_for("admin_products_tab"))
        except Exception as e:
            db.session.rollback()
            print(f"Edit Product Error: {e}")
            flash("Failed to update product.")
            return redirect(url_for("admin_edit_product", product_id=product_id))

    return render_template("admin_product_form.html", product=product, mode="edit")


@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        product.is_active = False
        db.session.commit()
        flash(f"Product '{product.name}' moved to deleted list.")
    except Exception as e:
        db.session.rollback()
        print(f"Delete Error: {e}")
        flash("Failed to delete product.")
    return redirect(url_for("admin_products_tab") + "#active")


@app.route("/admin/products/restore/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def admin_restore_product(product_id):
    product = Product.query.get_or_404(product_id)
    try:
        product.is_active = True
        db.session.commit()
        flash(f"Product '{product.name}' restored successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Restore Error: {e}")
        flash("Failed to restore product.")
    return redirect(url_for("admin_products_tab") + "#deleted")


@app.route("/admin/products/permanent-delete/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def admin_permanent_delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.is_active:
        flash("Pehle product ko delete karo, phir permanently delete ho paayega.")
        return redirect(url_for("admin_products_tab") + "#active")

    product_name = product.name
    image_urls = [product.image, product.image2, product.image3, product.image4]
    image_urls = [u for u in image_urls if u]

    try:
        for url in image_urls:
            _delete_cloudinary_image(url)
        db.session.delete(product)
        db.session.commit()
        flash(f"Product '{product_name}' permanently deleted. 🙏")
    except Exception as e:
        db.session.rollback()
        print(f"Permanent Delete Error: {e}")
        flash("Failed to permanently delete product.")

    return redirect(url_for("admin_products_tab") + "#deleted")


# ==================================================
# ADMIN — ORDER STATUS UPDATE
# ==================================================

@app.route("/admin/order/<int:order_id>/update-status", methods=["POST"])
@login_required
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = sanitize_string(request.form.get("status", "").lower(), 20)
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]

    if new_status not in valid_statuses:
        flash("Invalid order status.")
        return redirect(url_for("admin_orders_tab"))

    old_status = order.status

    try:
        if new_status == "cancelled" and old_status != "cancelled":
            for item in order.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity

        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} status updated to {new_status}.")

        if old_status != new_status:
            try:
                if new_status == "cancelled":
                    send_order_cancelled_email(order, order.user)
                else:
                    send_status_update_email(order, order.user, old_status, new_status)
            except Exception as e:
                print(f"Status update email error: {e}")

    except Exception as e:
        db.session.rollback()
        print(f"Status Update Error: {e}")
        flash("Failed to update order status.")

    redirect_params = {}
    for k in ["q", "status", "sort", "page"]:
        val = request.form.get(f"return_{k}")
        if val:
            redirect_params[k] = val

    return redirect(url_for("admin_orders_tab", **redirect_params))


@app.route("/admin/order/<int:order_id>")
@login_required
@admin_required
def admin_order_details(order_id):
    order = Order.query.options(
        joinedload(Order.user), joinedload(Order.items)
    ).get_or_404(order_id)
    return render_template("admin_order_details.html", order=order)


# ==================================================
# ERROR HANDLERS
# ==================================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(error):
    flash("You don't have permission to access this page.")
    return redirect(url_for("home")), 403


@app.errorhandler(429)
def ratelimit_handler(error):
    flash("Too many requests. Please slow down and try again later.")
    return redirect(url_for("home")), 429


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash("Your session expired. Please try again.")
    return redirect(url_for("home"))


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    print(f"500 Error: {error}")
    return render_template("404.html"), 500


# ==================================================
# STARTUP — DATABASE INIT & SEED
# ==================================================

def initialize_database():
    with app.app_context():
        try:
            db.create_all()
            print("✅ Database tables ready!")
        except Exception as e:
            print(f"❌ DB create error: {e}")
            return

        # Admin user
        try:
            admin_email = app.config.get("ADMIN_EMAIL", "admin@zenith.com")
            admin_password = app.config.get("ADMIN_PASSWORD", "Admin@123")
            admin_user = User.query.filter_by(email=admin_email).first()

            if not admin_user:
                admin_user = User(
                    full_name="Admin", email=admin_email,
                    phone="+919999999999",
                    password=generate_password_hash(admin_password),
                    is_admin=True
                )
                db.session.add(admin_user)
                db.session.commit()
                print(f"✅ Admin created: {admin_email}")
            else:
                print(f"✅ Admin exists: {admin_email}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Admin setup error: {e}")

        # Seed products
        try:
            if Product.query.count() == 0:
                seed_products = [
                    {"name": "Premium White T-Shirt", "price": 799, "old_price": 999, "image": "images/products/tshirt.jpg", "rating": 4.9, "description": "Premium cotton t-shirt made from soft breathable fabric.", "category": "featured", "subcategory": "men,tshirt", "sizes": "S,M,L,XL,XXL", "colors": "white", "brand": "Zenith"},
                    {"name": "Premium Black Jeans", "price": 1499, "old_price": 1899, "image": "images/products/jeans.jpg", "rating": 4.8, "description": "Comfort fit black jeans made from premium stretch denim.", "category": "featured", "subcategory": "men,jeans", "sizes": "28,30,32,34,36", "colors": "black", "brand": "Zenith"},
                    {"name": "Premium White Shoes", "price": 2999, "old_price": 3499, "image": "images/products/shoes.jpg", "rating": 5.0, "description": "Premium lightweight sneakers with soft cushioning.", "category": "featured", "subcategory": "men,shoes", "sizes": "6,7,8,9,10,11", "colors": "white", "brand": "Zenith"},
                    {"name": "Black Bomber Jacket", "price": 2499, "old_price": 2999, "image": "images/bestsellers/jacket.jpg", "rating": 4.8, "description": "Stylish bomber jacket perfect for winter fashion.", "category": "bestseller", "subcategory": "men,jacket", "sizes": "S,M,L,XL,XXL", "colors": "black", "brand": "Zenith"},
                    {"name": "White Premium Sneakers", "price": 3999, "old_price": 4499, "image": "images/bestsellers/sneakers.jpg", "rating": 5.0, "description": "Luxury sneakers built for comfort.", "category": "bestseller", "subcategory": "men,shoes", "sizes": "6,7,8,9,10,11", "colors": "white", "brand": "Zenith"},
                    {"name": "Black Urban Cap", "price": 699, "old_price": 899, "image": "images/bestsellers/cap.jpg", "rating": 4.7, "description": "Premium cotton adjustable cap.", "category": "bestseller", "subcategory": "men,cap", "sizes": "S,M,L,XL", "colors": "white,black", "brand": "Zenith"},
                    {"name": "Premium Backpack", "price": 1899, "old_price": 2299, "image": "images/bestsellers/backpack.jpg", "rating": 4.9, "description": "Large capacity premium backpack.", "category": "bestseller", "subcategory": "men,backpack", "sizes": "S,M,L,XL", "colors": "white,black", "brand": "Zenith"},
                ]
                for p in seed_products:
                    db.session.add(Product(**p))
                db.session.commit()
                print(f"✅ Seeded {len(seed_products)} products!")
            else:
                print(f"✅ Products already exist: {Product.query.count()}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Seed error: {e}")

        # ✅ Seed default coupons
        try:
            if Coupon.query.count() == 0:
                seed_coupons = app.config.get("SEED_COUPONS", [])
                for c in seed_coupons:
                    db.session.add(Coupon(**c))
                db.session.commit()
                print(f"✅ Seeded {len(seed_coupons)} coupons!")
            else:
                print(f"✅ Coupons already exist: {Coupon.query.count()}")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Coupon seed error: {e}")


# Run DB init at import time (works with gunicorn)
initialize_database()


# ==================================================
# RUN APPLICATION (local only)
# ==================================================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    debug_mode = app.config.get("FLASK_ENV") != "production"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)