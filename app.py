from flask import Flask, render_template, abort, redirect, url_for, request, flash, jsonify

from config import Config
from models import db, User, Order, OrderItem, Product

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from flask_mail import Mail, Message

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from functools import wraps
import re
import secrets
import json
import os
import razorpay
from datetime import datetime, timedelta


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
# EMAIL CONFIGURATION
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
    storage_uri="memory://"
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


# ==================================================
# USER LOADER
# ==================================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# ==================================================
# VALIDATION HELPERS
# ==================================================

def is_valid_email(email):
    """Basic email validation"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_phone(phone):
    """Basic phone validation (10-15 digits, optional +, spaces, dashes)"""
    pattern = r'^\+?[\d\s\-]{10,15}$'
    return re.match(pattern, phone) is not None


def is_strong_password(password):
    """Check password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter."

    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter."

    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number."

    return True, "Password is strong."


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
        category="featured",
        is_active=True
    ).all()

    best_sellers_db = Product.query.filter_by(
        category="bestseller",
        is_active=True
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

    product_db = Product.query.get(product_id)

    if product_db is None or not product_db.is_active:
        abort(404)

    return render_template(
        "product.html",
        product=product_db.to_dict()
    )


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
# SIGNUP PAGE (Rate Limited)
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

        if not full_name or not email or not phone or not password or not confirm_password:
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

        hashed_password = generate_password_hash(password)

        new_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully! Please login.")
        return redirect(url_for("login"))

    return render_template("signup.html")


# ==================================================
# USER LOGIN PAGE (Rate Limited)
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
# ADMIN LOGIN PAGE (Rate Limited)
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

        flash("Invalid admin credentials. Please check email and password.")
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
# FORGOT PASSWORD (Rate Limited)
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
            token = secrets.token_hex(32)

            user.reset_token = token
            user.reset_token_expiry = datetime.utcnow() + timedelta(hours=1)

            db.session.commit()

            reset_link = url_for("reset_password", token=token, _external=True)

            try:
                msg = Message(
                    subject="UrbanWear - Password Reset Link",
                    recipients=[email],
                    html=f"""
                    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 30px; background: #faf8f5;">
                        <div style="text-align: center; padding: 20px 0; border-bottom: 2px solid #c9a961;">
                            <h1 style="color: #1a1a1a; font-family: Georgia, serif; margin: 0; font-size: 28px;">
                                Urban<span style="color: #c9a961; font-style: italic;">Wear</span>
                            </h1>
                        </div>

                        <div style="padding: 40px 30px; background: #ffffff;">
                            <h2 style="color: #1a1a1a; font-family: Georgia, serif; font-weight: 500;">Password Reset Request</h2>

                            <p style="color: #555; line-height: 1.7; font-size: 15px;">
                                Hi <strong>{user.full_name}</strong>,
                            </p>

                            <p style="color: #555; line-height: 1.7; font-size: 15px;">
                                We received a request to reset your UrbanWear account password.
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
                            © 2026 UrbanWear. All Rights Reserved.
                        </div>
                    </div>
                    """
                )

                mail.send(msg)

                flash("Password reset link has been sent to your email! Please check your inbox (and spam folder).")
                return redirect(url_for("login"))

            except Exception as e:
                print(f"❌ Email Error: {e}")
                flash("Failed to send email. Please try again later.")
                return redirect(url_for("forgot_password"))

        flash("Email not found. Please check and try again.")
        return redirect(url_for("forgot_password"))

    return render_template("forgot_password.html")


# ==================================================
# RESET PASSWORD (Rate Limited)
# ==================================================

@app.route("/reset-password/<token>", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def reset_password(token):

    user = User.query.filter_by(reset_token=token).first()

    if not user:
        flash("Invalid or expired reset link.")
        return redirect(url_for("forgot_password"))

    if user.reset_token_expiry < datetime.utcnow():
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
# PROFILE PAGE
# ==================================================

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)


# ==================================================
# UPDATE PROFILE
# ==================================================

@app.route("/profile/update", methods=["POST"])
@login_required
def update_profile():

    full_name = request.form.get("full_name", "").strip()
    phone = request.form.get("phone", "").strip()

    if not full_name or not phone:
        flash("All fields are required.")
        return redirect(url_for("profile"))

    current_user.full_name = full_name
    current_user.phone = phone

    db.session.commit()

    flash("Profile updated successfully!")
    return redirect(url_for("profile"))


# ==================================================
# CHECKOUT PAGE
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
        payment_method = request.form.get("payment_method", "cod")

        if not full_name or not address or not city or not state or not pincode:
            flash("All fields are required.")
            return redirect(url_for("checkout"))

        cart_data = request.form.get("cart_data", "[]")
        cart_items = json.loads(cart_data)

        if not cart_items:
            flash("Your cart is empty.")
            return redirect(url_for("cart"))

        total_amount = sum(item["price"] * item["quantity"] for item in cart_items)

        shipping_address = f"{address}, {city}, {state} - {pincode}"

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

        for item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=item["id"],
                product_name=item["name"],
                price=item["price"],
                quantity=item["quantity"],
                size=item.get("size"),
                color=item.get("color")
            )
            db.session.add(order_item)

        db.session.commit()

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
# PAYMENT - CREATE RAZORPAY ORDER (CSRF EXEMPT)
# ==================================================

@app.route("/payment/create-order", methods=["POST"])
@login_required
@csrf.exempt
def create_payment_order():

    try:
        data = request.get_json()
        amount = int(float(data.get("amount", 0)) * 100)

        if amount <= 0:
            return jsonify({"error": "Invalid amount"}), 400

        razorpay_order = razorpay_client.order.create({
            "amount": amount,
            "currency": "INR",
            "receipt": f"receipt_{current_user.id}_{int(datetime.utcnow().timestamp())}",
            "payment_capture": 1
        })

        return jsonify({
            "order_id": razorpay_order["id"],
            "amount": razorpay_order["amount"],
            "currency": razorpay_order["currency"],
            "key_id": app.config["RAZORPAY_KEY_ID"]
        })

    except Exception as e:
        print(f"Razorpay Error: {e}")
        return jsonify({"error": str(e)}), 500


# ==================================================
# PAYMENT - VERIFY (CSRF EXEMPT)
# ==================================================

@app.route("/payment/verify", methods=["POST"])
@login_required
@csrf.exempt
def verify_payment():

    try:
        data = request.get_json()

        razorpay_payment_id = data.get("razorpay_payment_id")
        razorpay_order_id = data.get("razorpay_order_id")
        razorpay_signature = data.get("razorpay_signature")
        order_id = data.get("order_id")

        params_dict = {
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature
        }

        razorpay_client.utility.verify_payment_signature(params_dict)

        order = Order.query.get(order_id)

        if order:
            order.payment_id = razorpay_payment_id
            order.razorpay_order_id = razorpay_order_id
            order.payment_status = "paid"
            order.status = "processing"
            db.session.commit()

        return jsonify({"status": "success", "payment_id": razorpay_payment_id})

    except razorpay.errors.SignatureVerificationError:
        return jsonify({"status": "failed", "error": "Signature verification failed"}), 400

    except Exception as e:
        return jsonify({"status": "failed", "error": str(e)}), 500


# ==================================================
# PAYMENT SUCCESS
# ==================================================

@app.route("/payment-success/<int:order_id>")
@login_required
def payment_success(order_id):

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)

    return render_template("payment_success.html", order=order)


# ==================================================
# PAYMENT FAILURE
# ==================================================

@app.route("/payment-failure/<int:order_id>")
@login_required
def payment_failure(order_id):

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)

    return render_template("payment_failure.html", order=order)


# ==================================================
# ORDER SUCCESS PAGE
# ==================================================

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

    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()

    return render_template("orders.html", orders=user_orders)


# ==================================================
# USER - CANCEL ORDER
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

    order.status = "cancelled"

    db.session.commit()

    flash("Order cancelled successfully.")
    return redirect(url_for("orders"))


# ==================================================
# USER - ORDER DETAILS
# ==================================================

@app.route("/order/<int:order_id>")
@login_required
def order_details(order_id):

    order = Order.query.get_or_404(order_id)

    if order.user_id != current_user.id:
        abort(403)

    return render_template("order_details.html", order=order)


# ==================================================
# ADMIN PANEL (MAIN)
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

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    return render_template("admin_panel.html",
                         total_orders=total_orders,
                         total_users=total_users,
                         total_revenue=total_revenue,
                         pending_orders=pending_orders,
                         total_products=total_products,
                         recent_orders=recent_orders)


# ==================================================
# ADMIN - ORDERS TAB
# ==================================================

@app.route("/admin/orders")
@login_required
@admin_required
def admin_orders_tab():

    all_orders = Order.query.order_by(Order.created_at.desc()).all()

    return render_template("admin_panel.html",
                         active_tab="orders",
                         orders=all_orders)


# ==================================================
# ADMIN - PRODUCTS TAB
# ==================================================

@app.route("/admin/products")
@login_required
@admin_required
def admin_products_tab():

    all_products = Product.query.order_by(Product.created_at.desc()).all()

    return render_template("admin_panel.html",
                         active_tab="products",
                         products=all_products)


# ==================================================
# ADMIN - ADD PRODUCT
# ==================================================

@app.route("/admin/products/add", methods=["GET", "POST"])
@login_required
@admin_required
def admin_add_product():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        price = request.form.get("price", "").strip()
        old_price = request.form.get("old_price", "").strip()
        image = request.form.get("image", "").strip()
        image2 = request.form.get("image2", "").strip()
        image3 = request.form.get("image3", "").strip()
        image4 = request.form.get("image4", "").strip()
        rating = request.form.get("rating", "4.5").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "featured").strip()
        stock = request.form.get("stock", "10").strip()

        if not name or not price or not image:
            flash("Name, Price, and Image are required.")
            return redirect(url_for("admin_add_product"))

        try:
            new_product = Product(
                name=name,
                price=float(price),
                old_price=float(old_price) if old_price else None,
                image=image,
                image2=image2 or None,
                image3=image3 or None,
                image4=image4 or None,
                rating=float(rating) if rating else 4.5,
                description=description,
                category=category,
                stock=int(stock) if stock else 10,
                is_active=True
            )

            db.session.add(new_product)
            db.session.commit()

            flash(f"Product '{name}' added successfully!")
            return redirect(url_for("admin_products_tab"))

        except Exception as e:
            print(f"Error: {e}")
            flash("Failed to add product. Please check all fields.")
            return redirect(url_for("admin_add_product"))

    return render_template("admin_product_form.html", product=None, mode="add")


# ==================================================
# ADMIN - EDIT PRODUCT
# ==================================================

@app.route("/admin/products/edit/<int:product_id>", methods=["GET", "POST"])
@login_required
@admin_required
def admin_edit_product(product_id):

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":

        product.name = request.form.get("name", "").strip()
        product.price = float(request.form.get("price", 0))
        product.old_price = float(request.form.get("old_price", 0)) if request.form.get("old_price") else None
        product.image = request.form.get("image", "").strip()
        product.image2 = request.form.get("image2", "").strip() or None
        product.image3 = request.form.get("image3", "").strip() or None
        product.image4 = request.form.get("image4", "").strip() or None
        product.rating = float(request.form.get("rating", 4.5))
        product.description = request.form.get("description", "").strip()
        product.category = request.form.get("category", "featured").strip()
        product.stock = int(request.form.get("stock", 10))

        db.session.commit()

        flash(f"Product '{product.name}' updated successfully!")
        return redirect(url_for("admin_products_tab"))

    return render_template("admin_product_form.html", product=product, mode="edit")


# ==================================================
# ADMIN - DELETE PRODUCT
# ==================================================

@app.route("/admin/products/delete/<int:product_id>", methods=["POST"])
@login_required
@admin_required
def admin_delete_product(product_id):

    product = Product.query.get_or_404(product_id)

    product_name = product.name

    db.session.delete(product)
    db.session.commit()

    flash(f"Product '{product_name}' deleted successfully!")
    return redirect(url_for("admin_products_tab"))


# ==================================================
# ADMIN - USERS TAB
# ==================================================

@app.route("/admin/users")
@login_required
@admin_required
def admin_users_tab():

    all_users = User.query.order_by(User.created_at.desc()).all()

    return render_template("admin_panel.html",
                         active_tab="users",
                         users=all_users)


# ==================================================
# ADMIN - UPDATE ORDER STATUS
# ==================================================

@app.route("/admin/order/<int:order_id>/update-status", methods=["POST"])
@login_required
@admin_required
def admin_update_order_status(order_id):

    order = Order.query.get_or_404(order_id)

    new_status = request.form.get("status", "").strip()

    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]

    if new_status not in valid_statuses:
        flash("Invalid order status.")
        return redirect(url_for("admin_orders_tab"))

    order.status = new_status

    db.session.commit()

    flash(f"Order #{order.id} status updated to {new_status}.")
    return redirect(url_for("admin_orders_tab"))


# ==================================================
# ADMIN - ORDER DETAILS
# ==================================================

@app.route("/admin/order/<int:order_id>")
@login_required
@admin_required
def admin_order_details(order_id):

    order = Order.query.get_or_404(order_id)

    return render_template("admin_order_details.html", order=order)


# ==================================================
# ERROR HANDLERS
# ==================================================

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404


@app.errorhandler(429)
def ratelimit_handler(error):
    flash("Too many requests. Please slow down and try again later.")
    return redirect(url_for("home")), 429


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    os.makedirs(instance_path, exist_ok=True)

    with app.app_context():
        db.create_all()
        print("✅ Database tables created successfully!")
        print("✅ Users table ready!")
        print("✅ Orders table ready!")
        print("✅ Order items table ready!")
        print("✅ Products table ready!")

        admin_email = "admin@urbanwear.com"
        admin_user = User.query.filter_by(email=admin_email).first()

        if not admin_user:
            admin_user = User(
                full_name="Admin",
                email=admin_email,
                phone="+919999999999",
                password=generate_password_hash("admin123"),
                is_admin=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Admin user created!")
            print("✅ Admin Email: admin@urbanwear.com")
            print("✅ Admin Password: admin123")
        else:
            print("✅ Admin user already exists.")

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
                new_product = Product(**p)
                db.session.add(new_product)

            db.session.commit()
            print(f"✅ Seeded {len(seed_products)} products into database!")
        else:
            print(f"✅ Products already exist: {Product.query.count()} products found.")

    app.run(debug=True)