from flask import Flask, render_template, abort, redirect, url_for, request, flash

from config import Config
from models import db, User

from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
    current_user
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


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
# PRODUCT DATABASE
# ==================================================

products = {

    1: {
        "id": 1,
        "name": "Premium White T-Shirt",
        "price": 799,
        "old_price": 999,
        "image": "images/products/tshirt.jpg",
         "images": [
        "images/products/tshirt.jpg",
        "images/products/tshirt.jpg",
        "images/products/tshirt.jpg",
        "images/products/tshirt.jpg"
    ],
        "rating": 4.9,
        "description": "Premium cotton t-shirt made from soft breathable fabric. Perfect for casual wear.",
        "category": "featured"
    },

    2: {
        "id": 2,
        "name": "Premium Black Jeans",
        "price": 1499,
        "old_price": 1899,
        "image": "images/products/jeans.jpg",
        "images": [
    "images/products/jeans.jpg",
    "images/products/jeans.jpg",
    "images/products/jeans.jpg",
    "images/products/jeans.jpg"
],
        "rating": 4.8,
        "description": "Comfort fit black jeans made from premium stretch denim.",
        "category": "featured"
    },

    3: {
        "id": 3,
        "name": "Premium White Shoes",
        "price": 2999,
        "old_price": 3499,
        "image": "images/products/shoes.jpg",
        "images": [
    "images/products/shoes.jpg",
    "images/products/shoes.jpg",
    "images/products/shoes.jpg",
    "images/products/shoes.jpg"
],
        "rating": 5.0,
        "description": "Premium lightweight sneakers with soft cushioning and modern design.",
        "category": "featured"
    },

    4: {
        "id": 4,
        "name": "Black Bomber Jacket",
        "price": 2499,
        "old_price": 2999,
        "image": "images/bestsellers/jacket.jpg",
        "images": [
    "images/bestsellers/jacket.jpg",
    "images/bestsellers/jacket.jpg",
    "images/bestsellers/jacket.jpg",
    "images/bestsellers/jacket.jpg"
],
        "rating": 4.8,
        "description": "Stylish bomber jacket perfect for winter fashion.",
        "category": "bestseller"
    },

    5: {
        "id": 5,
        "name": "White Premium Sneakers",
        "price": 3999,
        "old_price": 4499,
        "image": "images/bestsellers/sneakers.jpg",
        "images": [
    "images/bestsellers/sneakers.jpg",
    "images/bestsellers/sneakers.jpg",
    "images/bestsellers/sneakers.jpg",
    "images/bestsellers/sneakers.jpg"
],
        "rating": 5.0,
        "description": "Luxury sneakers built for comfort and everyday wear.",
        "category": "bestseller"
    },

    6: {
        "id": 6,
        "name": "Black Urban Cap",
        "price": 699,
        "old_price": 899,
        "image": "images/bestsellers/cap.jpg",
        "images": [
    "images/bestsellers/cap.jpg",
    "images/bestsellers/cap.jpg",
    "images/bestsellers/cap.jpg",
    "images/bestsellers/cap.jpg"
],
        "rating": 4.7,
        "description": "Premium cotton adjustable cap for daily style.",
        "category": "bestseller"
    },

    7: {
        "id": 7,
        "name": "Premium Backpack",
        "price": 1899,
        "old_price": 2299,
        "image": "images/bestsellers/backpack.jpg",
        "images": [
    "images/bestsellers/backpack.jpg",
    "images/bestsellers/backpack.jpg",
    "images/bestsellers/backpack.jpg",
    "images/bestsellers/backpack.jpg"
],
        "rating": 4.9,
        "description": "Large capacity premium backpack with laptop compartment.",
        "category": "bestseller"
    }

}

# ==================================================
# HOME PAGE
# ==================================================

@app.route("/")
def home():

    featured_products = [
        p for p in products.values()
        if p["category"] == "featured"
    ]

    best_sellers = [
        p for p in products.values()
        if p["category"] == "bestseller"
    ]

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

    product = products.get(product_id)

    if product is None:
        abort(404)

    return render_template(
        "product.html",
        product=product
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
# SIGNUP PAGE
# ==================================================

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        # ==========================
        # Get Form Data
        # ==========================
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # ==========================
        # Empty Field Validation
        # ==========================
        if not full_name or not email or not phone or not password or not confirm_password:
            flash("All fields are required.")
            return redirect(url_for("signup"))

        # ==========================
        # Confirm Password Validation
        # ==========================
        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("signup"))

        # ==========================
        # Duplicate Email Check
        # ==========================
        existing_user = User.query.filter_by(email=email).first()

        if existing_user:
            flash("Email already registered.")
            return redirect(url_for("signup"))

        # ==========================
        # Password Hashing
        # ==========================
        hashed_password = generate_password_hash(password)

        # ==========================
        # Create User
        # ==========================
        new_user = User(
            full_name=full_name,
            email=email,
            phone=phone,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully.")
        return redirect(url_for("signup"))

    return render_template("signup.html")


# ==================================================
# LOGIN PAGE
# ==================================================

@app.route("/login", methods=["GET", "POST"])
def login():

    # ==========================
    # ALREADY LOGGED IN
    # ==========================

    if current_user.is_authenticated:
        return redirect(url_for("home"))

    # ==========================
    # POST REQUEST
    # ==========================

    if request.method == "POST":

        # ==========================
        # GET FORM DATA
        # ==========================

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember") == "on"

        # ==========================
        # EMPTY FIELD VALIDATION
        # ==========================

        if not email or not password:

            flash("Email and password are required.")

            return redirect(url_for("login"))

        # ==========================
        # FIND USER
        # ==========================

        user = User.query.filter_by(email=email).first()

        # ==========================
        # VERIFY PASSWORD
        # ==========================

        if user and check_password_hash(user.password, password):

            login_user(user, remember=remember)

            flash("Login successful!")

            return redirect(url_for("home"))

        # ==========================
        # INVALID LOGIN
        # ==========================

        flash("Invalid email or password.")

        return redirect(url_for("login"))

    # ==========================
    # SHOW LOGIN PAGE
    # ==========================

    return render_template("login.html")


# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
@login_required
def logout():

    # ==========================
    # LOGOUT USER
    # ==========================

    logout_user()

    # ==========================
    # SUCCESS MESSAGE
    # ==========================

    flash("You have been logged out successfully.")

    # ==========================
    # REDIRECT HOME
    # ==========================

    return redirect(url_for("home"))


# ==================================================
# CUSTOM 404 PAGE
# ==================================================

@app.errorhandler(404)
def page_not_found(error):
    return "<h1>404 - Product Not Found</h1>", 404


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True)