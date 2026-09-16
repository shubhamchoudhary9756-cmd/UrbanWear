"""
Zenith - Flask E-Commerce Application
"""
import warnings

# Suppress harmless requests dependency warning
warnings.filterwarnings(
    "ignore",
    message=".*Unable to find acceptable character detection.*"
)

from flask import (
    Flask, render_template, abort, redirect, url_for,
    request, flash, jsonify
)

from config import Config
from models import db, User, Order, OrderItem, Product, utc_now

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

from sqlalchemy.orm import joinedload

from functools import wraps
import re
import secrets
import json
import os
import razorpay
from datetime import datetime, timedelta, timezone


# ==================================================
# FLASK APPLICATION
# ==================================================

app = Flask(__name__)

app.config.from_object(Config)


# ==================================================
# DATABASE
# ==================================================

db.init_app(app)


# ==================================================
# EMAIL
# ==================================================

mail = Mail(app)


# ==================================================
# CSRF PROTECTION
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
# VALIDATION HELPERS
# ==================================================

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{9,14}$')


def is_valid_email(email):
    """Strict email validation"""
    if not email or len(email) > 120:
        return False
    return EMAIL_REGEX.match(email) is not None


def is_valid_phone(phone):
    """Strict phone validation (10-15 digits, optional +)"""
    if not phone:
        return False
    clean_phone = re.sub(r'[\s\-]', '', phone)
    return PHONE_REGEX.match(clean_phone) is not None


def is_strong_password(password):
    """Check password strength"""
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
    """Safely convert to int"""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value, default=0.0):
    """Safely convert to float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


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

    featured_products = [p.to_dict() for p in featured_products_db]
    best_sellers = [p.to_dict() for p in best_sellers_db]

    return render_template(
        "index.html",
        featured_products=featured_products,
        best_sellers=best_sellers
    )


# ==================================================
# PRODUCT DETAILS
# ==================================================

@app.route("/product/<int:product_id>")
def product(product_id):
    product_db = db.session.get(Product, product_id)

    if product_db is None or not product_db.is_active:
        abort(404)

    return render_template("product.html", product=product_db.to_dict())


# ==================================================
# CART PAGE
# ==================================================

@app.route("/cart")
def cart():
    return render_template("cart.html")


# ==================================================
# WISHLIST PAGE
# ==================================================

@app.route("/wishlist")
def wishlist():
    return render_template("wishlist.html")


# ==================================================
# SIGNUP
# ==================================================

@app.route("/signup", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def signup():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not all([full_name, email, phone, password, confirm_password]):
            flash("All fields are required.")
            return redirect(url_for("signup"))

        if len(full_name) > 100:
            flash("Name is too long.")
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
            full_name=full_name,
            email=email,
            phone=phone,
            password=generate_password_hash(password)
        )

        try:
            db.session.add(new_user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Signup Error: {e}")
            flash("Something went wrong. Please try again.")
            return redirect(url_for("signup"))

        flash("Account created successfully! Please login.")
        return redirect(url_for("login"))

    return render_template("signup.html")


# ==================================================
# USER LOGIN
# ==================================================

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute", methods=["POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_panel"))
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
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
        email = request.form.get("email", "").strip().lower()
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
# FORGOT PASSWORD
# ==================================================

@app.route("/forgot-password", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

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

            try:
                msg = Message(
                    subject="Zenith - Password Reset Link",
                    recipients=[email],
                    html=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #faf8f5;">
                        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #c9a961;">
                            <h1 style="color: #1a1a1a; font-family: Georgia, serif; margin: 0; font-size: 28px; letter-spacing: 3px;">
                                ZENITH
                            </h1>
                            <p style="color: #c9a961; font-size: 12px; letter-spacing: 2px; margin: 5px 0 0 0;">
                                WEAR THE PEAK
                            </p>
                        </div>
                        <div style="padding: 40px 30px; background: #ffffff;">
                            <h2 style="color: #1a1a1a; font-family: Georgia, serif; font-weight: 500;">Password Reset Request</h2>
                            <p style="color: #555; line-height: 1.7; font-size: 15px;">
                                Hi <strong>{user.full_name}</strong>,
                            </p>
                            <p style="color: #555; line-height: 1.7; font-size: 15px;">
                                We received a request to reset your Zenith account password.
                                Click the button below to create a new password.
                            </p>
                            <div style="text-align: center; margin: 35px 0;">
                                <a href="{reset_link}"
                                   style="display: inline-block; padding: 16px 40px; background: #1a1a1a; color: #ffffff; text-decoration: none; letter-spacing: 1.5px; font-size: 13px; text-transform: uppercase; font-weight: 600;">
                                    Reset Password
                                </a>
                            </div>
                            <p style="color: #999; font-size: 13px; line-height: 1.7;">
                                This link will expire in <strong>1 hour</strong>.
                            </p>
                            <p style="color: #999; font-size: 13px; line-height: 1.7;">
                                If you didn't request this, you can safely ignore this email.
                            </p>
                        </div>
                        <div style="text-align: center; padding: 20px 0; color: #999; font-size: 12px;">
                            © 2026 Zenith. All Rights Reserved.
                        </div>
                    </div>
                    """
                )
                mail.send(msg)
            except Exception as e:
                print(f"❌ Email Error: {e}")

        # ✅ SECURITY: Same message regardless of email existence
        flash("If this email is registered, a reset link has been sent.")
        return redirect(url_for("login"))

    return render_template("forgot_password.html")


# ==================================================
# RESET PASSWORD
# ==================================================

@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):
    if not token or len(token) > 100:
        flash("Invalid reset link.")
        return redirect(url_for("forgot_password"))

    user = User.query.filter_by(reset_token=token).first()

    if not user:
        flash("Invalid or expired reset link.")
        return redirect(url_for("forgot_password"))

    if not user.reset_token_expiry or user.reset_token_expiry < utc_now():
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
    return render_template("profile.html", user=current_user)


@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():
    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not full_name or not phone:
        flash("All fields are required.")
        return redirect(url_for("profile"))

    if len(full_name) > 100:
        flash("Name is too long.")
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
# CHECKOUT (SECURED — SERVER-SIDE PRICE)
# ==================================================

@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        address = request.form.get("address", "").strip()
        city = request.form.get("city", "").strip()
        state = request.form.get("state", "").strip()
        pincode = request.form.get("pincode", "").strip()
        payment_method = request.form.get("payment_method", "cod").strip().lower()

        if not all([full_name, address, city, state, pincode]):
            flash("All fields are required.")
            return redirect(url_for("checkout"))

        if payment_method not in ["cod", "card", "upi"]:
            flash("Invalid payment method.")
            return redirect(url_for("checkout"))

        if len(pincode) > 10 or not pincode.isdigit():
            flash("Please enter a valid pincode.")
            return redirect(url_for("checkout"))

        # Parse cart data
        try:
            cart_data = request.form.get("cart_data", "[]")
            cart_items = json.loads(cart_data)
        except (json.JSONDecodeError, TypeError):
            flash("Invalid cart data.")
            return redirect(url_for("cart"))

        if not isinstance(cart_items, list) or not cart_items:
            flash("Your cart is empty.")
            return redirect(url_for("cart"))

        # ✅ SECURITY: Server-side price and stock validation
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
                flash(f"Product not available.")
                return redirect(url_for("cart"))

            if product.stock < quantity:
                flash(f"'{product.name}' sirf {product.stock} available hai.")
                return redirect(url_for("cart"))

            # ✅ Use DB price, not client price
            subtotal = product.price * quantity
            total_amount += subtotal

            validated_items.append({
                "product": product,
                "quantity": quantity,
                "size": item.get("size"),
                "color": item.get("color"),
                "price": product.price,
            })

        shipping_address = f"{address}, {city}, {state} - {pincode}"

        try:
            order = Order(
                user_id=current_user.id,
                total_amount=total_amount,
                status="pending",
                payment_method=payment_method,
                payment_status="pending",
                shipping_address=shipping_address
            )
            db.session.add(order)
            db.session.flush()

            for vi in validated_items:
                p = vi["product"]
                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=p.id,
                    product_name=p.name,
                    price=vi["price"],
                    quantity=vi["quantity"],
                    size=vi["size"],
                    color=vi["color"]
                ))
                # ✅ Decrement stock
                p.stock -= vi["quantity"]

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print(f"Checkout Error: {e}")
            flash("Failed to place order. Please try again.")
            return redirect(url_for("checkout"))

        if payment_method in ["card", "upi"]:
            return redirect(url_for("payment_page", order_id=order.id))

        flash("Order placed successfully!")
        return redirect(url_for("order_success", order_id=order.id))

    return render_template("checkout.html")


# ==================================================
# PAYMENT PAGE
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

    return render_template(
        "payment.html",
        order=order,
        razorpay_key_id=app.config["RAZORPAY_KEY_ID"]
    )


# ==================================================
# CREATE RAZORPAY ORDER (SECURED)
# ==================================================

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

        # ✅ SECURITY: Use DB amount, not client amount
        amount_paise = int(round(order.total_amount * 100))

        if amount_paise <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        razorpay_order = razorpay_client.order.create({
            "amount": amount_paise,
            "currency": "INR",
            "receipt": f"receipt_{order.id}",
            "payment_capture": 1
        })

        # ✅ Save razorpay_order_id for later verification
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


# ==================================================
# VERIFY PAYMENT (SECURED)
# ==================================================

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

        # ✅ Verify signature FIRST
        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }
        razorpay_client.utility.verify_payment_signature(params_dict)

        # ✅ Fetch order and validate ownership
        order = db.session.get(Order, order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # ✅ Validate razorpay_order_id matches
        if order.razorpay_order_id != razorpay_order_id:
            return jsonify({"error": "Order mismatch"}), 400

        # ✅ Idempotency — prevent double payment
        if order.payment_status == "paid":
            return jsonify({"status": "success", "already_paid": True})

        order.payment_id = razorpay_payment_id
        order.payment_status = "paid"
        order.status = "processing"
        db.session.commit()

        return jsonify({"status": "success", "payment_id": razorpay_payment_id})

    except razorpay.errors.SignatureVerificationError:
        db.session.rollback()
        return jsonify({"status": "failed", "error": "Signature verification failed"}), 400

    except Exception as e:
        db.session.rollback()
        print(f"Payment Verify Error: {e}")
        return jsonify({"status": "failed", "error": "Verification failed"}), 500


# ==================================================
# PAYMENT FAILED — AUTO CANCEL + STOCK RESTORE
# ==================================================

@app.route("/payment/failed/<int:order_id>", methods=["POST"])
@login_required
@csrf.exempt
@limiter.limit("20 per minute")
def payment_failed(order_id):
    """
    Called from frontend when Razorpay payment fails or popup is dismissed.
    Auto-cancels the order and restores stock.
    """
    try:
        order = db.session.get(Order, order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order.user_id != current_user.id:
            return jsonify({"error": "Unauthorized"}), 403

        # ✅ Already paid — nothing to do
        if order.payment_status == "paid":
            return jsonify({"status": "already_paid"}), 200

        # ✅ Already cancelled — idempotent
        if order.status == "cancelled":
            return jsonify({"status": "already_cancelled"}), 200

        # ✅ Restore stock
        for item in order.items:
            product = db.session.get(Product, item.product_id)
            if product:
                product.stock += item.quantity

        # ✅ Mark order cancelled
        order.status = "cancelled"
        order.payment_status = "failed"
        db.session.commit()

        return jsonify({"status": "cancelled"}), 200

    except Exception as e:
        db.session.rollback()
        print(f"Payment Failed Handler Error: {e}")
        return jsonify({"error": "Failed to process"}), 500


# ==================================================
# PAYMENT SUCCESS / FAILURE / ORDER SUCCESS
# ==================================================

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
# ORDERS PAGE
# ==================================================

@app.route("/orders")
@login_required
def orders():
    user_orders = Order.query.filter_by(
        user_id=current_user.id
    ).order_by(Order.created_at.desc()).all()

    return render_template("orders.html", orders=user_orders)


# ==================================================
# CANCEL ORDER (With Stock Restore)
# ==================================================

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
        # ✅ Restore stock
        for item in order.items:
            product = db.session.get(Product, item.product_id)
            if product:
                product.stock += item.quantity

        order.status = "cancelled"
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Cancel Error: {e}")
        flash("Failed to cancel order.")
        return redirect(url_for("orders"))

    flash("Order cancelled successfully.")
    return redirect(url_for("orders"))


# ==================================================
# ORDER DETAILS
# ==================================================

@app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id:
        abort(403)
    return render_template("order_details.html", order=order)


# ==================================================
# ADMIN — DASHBOARD
# ==================================================

@app.route("/admin")
@app.route("/admin/")
@login_required
@admin_required
def admin_panel():
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_revenue = db.session.query(db.func.sum(Order.total_amount)).scalar() or 0
    pending_orders = Order.query.filter_by(status="pending").count()
    total_products = Product.query.count()

    recent_orders = Order.query.options(
        joinedload(Order.user)
    ).order_by(Order.created_at.desc()).limit(5).all()

    return render_template(
        "admin_panel.html",
        total_orders=total_orders,
        total_users=total_users,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        total_products=total_products,
        recent_orders=recent_orders
    )


# ==================================================
# ADMIN — ORDERS TAB
# ==================================================

@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders_tab():
    all_orders = Order.query.options(
        joinedload(Order.user)
    ).order_by(Order.created_at.desc()).all()

    return render_template(
        "admin_panel.html",
        active_tab="orders",
        orders=all_orders
    )


# ==================================================
# ADMIN — PRODUCTS TAB
# ==================================================

@app.route("/admin/products")
@login_required
@admin_required
def admin_products_tab():
    all_products = Product.query.order_by(Product.created_at.desc()).all()
    return render_template(
        "admin_panel.html",
        active_tab="products",
        products=all_products
    )


# ==================================================
# ADMIN — ADD PRODUCT
# ==================================================

@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = safe_float(request.form.get("price"))
        old_price = safe_float(request.form.get("old_price"))
        image = request.form.get("image", "").strip()
        image2 = request.form.get("image2", "").strip()
        image3 = request.form.get("image3", "").strip()
        image4 = request.form.get("image4", "").strip()
        rating = safe_float(request.form.get("rating"), 4.5)
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "featured").strip()
        stock = safe_int(request.form.get("stock"), 10)

        if not name or price <= 0 or not image:
            flash("Name, Price (> 0), and Image are required.")
            return redirect(url_for("admin_add_product"))

        if category not in ["featured", "bestseller"]:
            flash("Invalid category.")
            return redirect(url_for("admin_add_product"))

        try:
            new_product = Product(
                name=name,
                price=price,
                old_price=old_price if old_price > 0 else None,
                image=image,
                image2=image2 or None,
                image3=image3 or None,
                image4=image4 or None,
                rating=rating if 0 <= rating <= 5 else 4.5,
                description=description,
                category=category,
                stock=max(0, stock),
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


# ==================================================
# ADMIN — EDIT PRODUCT
# ==================================================

@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        price = safe_float(request.form.get("price"))
        old_price = safe_float(request.form.get("old_price"))

        if not name or price <= 0:
            flash("Name and Price (> 0) are required.")
            return redirect(url_for("admin_edit_product", product_id=product_id))

        try:
            product.name = name
            product.price = price
            product.old_price = old_price if old_price > 0 else None
            product.image = request.form.get("image", "").strip() or product.image
            product.image2 = request.form.get("image2", "").strip() or None
            product.image3 = request.form.get("image3", "").strip() or None
            product.image4 = request.form.get("image4", "").strip() or None
            product.rating = safe_float(request.form.get("rating"), 4.5)
            product.description = request.form.get("description", "").strip()
            product.category = request.form.get("category", "featured").strip()
            product.stock = max(0, safe_int(request.form.get("stock"), 10))

            db.session.commit()
            flash(f"Product '{product.name}' updated successfully!")
            return redirect(url_for("admin_products_tab"))

        except Exception as e:
            db.session.rollback()
            print(f"Edit Product Error: {e}")
            flash("Failed to update product.")
            return redirect(url_for("admin_edit_product", product_id=product_id))

    return render_template("admin_product_form.html", product=product, mode="edit")


# ==================================================
# ADMIN — DELETE PRODUCT
# ==================================================

@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    try:
        # ✅ Soft delete (orders ka reference intact rahe)
        product.is_active = False
        db.session.commit()
        flash(f"Product '{product.name}' deleted successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"Delete Error: {e}")
        flash("Failed to delete product.")

    return redirect(url_for("admin_products_tab"))


# ==================================================
# ADMIN — USERS TAB
# ==================================================

@app.route("/admin/users")
@login_required
@admin_required
def admin_users_tab():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template(
        "admin_panel.html",
        active_tab="users",
        users=all_users
    )


# ==================================================
# ADMIN — UPDATE ORDER STATUS
# ==================================================

@app.route("/admin/order/<int:order_id>/update-status", methods=["POST"])
@login_required
@admin_required
def admin_update_order_status(order_id):
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get("status", "").strip().lower()

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]

    if new_status not in valid_statuses:
        flash("Invalid order status.")
        return redirect(url_for("admin_orders_tab"))

    try:
        # ✅ If cancelling, restore stock (once)
        if new_status == "cancelled" and order.status != "cancelled":
            for item in order.items:
                product = db.session.get(Product, item.product_id)
                if product:
                    product.stock += item.quantity

        order.status = new_status
        db.session.commit()
        flash(f"Order #{order.id} status updated to {new_status}.")

    except Exception as e:
        db.session.rollback()
        print(f"Status Update Error: {e}")
        flash("Failed to update order status.")

    return redirect(url_for("admin_orders_tab"))


# ==================================================
# ADMIN — ORDER DETAILS
# ==================================================

@app.route("/admin/order/<int:order_id>")
@login_required
@admin_required
def admin_order_details(order_id):
    order = Order.query.options(
        joinedload(Order.user),
        joinedload(Order.items)
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
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":
    instance_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "instance"
    )
    os.makedirs(instance_path, exist_ok=True)

    with app.app_context():
        db.create_all()
        print("✅ Database tables ready!")

        # ✅ Create admin from ENV (not hardcoded)
        admin_email = app.config["ADMIN_EMAIL"]
        admin_password = app.config["ADMIN_PASSWORD"]
        admin_user = User.query.filter_by(email=admin_email).first()

        if not admin_user:
            admin_user = User(
                full_name="Admin",
                email=admin_email,
                phone="+919999999999",
                password=generate_password_hash(admin_password),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print(f"✅ Admin created: {admin_email}")
        else:
            print(f"✅ Admin exists: {admin_email}")

        # Seed products
        if Product.query.count() == 0:
            seed_products = [
                {"name": "Premium White T-Shirt", "price": 799, "old_price": 999, "image": "images/products/tshirt.jpg", "rating": 4.9, "description": "Premium cotton t-shirt made from soft breathable fabric.", "category": "featured"},
                {"name": "Premium Black Jeans", "price": 1499, "old_price": 1899, "image": "images/products/jeans.jpg", "rating": 4.8, "description": "Comfort fit black jeans made from premium stretch denim.", "category": "featured"},
                {"name": "Premium White Shoes", "price": 2999, "old_price": 3499, "image": "images/products/shoes.jpg", "rating": 5.0, "description": "Premium lightweight sneakers with soft cushioning.", "category": "featured"},
                {"name": "Black Bomber Jacket", "price": 2499, "old_price": 2999, "image": "images/bestsellers/jacket.jpg", "rating": 4.8, "description": "Stylish bomber jacket perfect for winter fashion.", "category": "bestseller"},
                {"name": "White Premium Sneakers", "price": 3999, "old_price": 4499, "image": "images/bestsellers/sneakers.jpg", "rating": 5.0, "description": "Luxury sneakers built for comfort.", "category": "bestseller"},
                {"name": "Black Urban Cap", "price": 699, "old_price": 899, "image": "images/bestsellers/cap.jpg", "rating": 4.7, "description": "Premium cotton adjustable cap.", "category": "bestseller"},
                {"name": "Premium Backpack", "price": 1899, "old_price": 2299, "image": "images/bestsellers/backpack.jpg", "rating": 4.9, "description": "Large capacity premium backpack.", "category": "bestseller"},
            ]
            for p in seed_products:
                db.session.add(Product(**p))
            db.session.commit()
            print(f"✅ Seeded {len(seed_products)} products!")
        else:
            print(f"✅ Products already exists: {Product.query.count()}")

    # ✅ Production me host 0.0.0.0 aur PORT env variable use karein
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("FLASK_ENV") != "production")