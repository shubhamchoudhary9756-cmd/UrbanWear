"""
Zenith - Database Models
+ Performance indexes for faster queries
+ Coupon model for discount system
+ Review model for ratings & reviews system
+ ✅ Product sizes & colors for frontend filters
"""

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


# ==================================================
# UTC NOW HELPER
# ==================================================

def utc_now():
    """Timezone-aware UTC now"""
    return datetime.now(timezone.utc)


# ==================================================
# USER MODEL
# ==================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)

    password = db.Column(db.String(255), nullable=False)

    is_admin = db.Column(db.Boolean, default=False)

    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    orders = db.relationship(
        "Order",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    reviews = db.relationship(
        "Review",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ✅ PERFORMANCE INDEXES
    __table_args__ = (
        db.Index("idx_user_is_admin", "is_admin"),
        db.Index("idx_user_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<User {self.email}>"

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================================================
# PRODUCT MODEL
# ==================================================

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float, nullable=True)

    image = db.Column(db.String(255), nullable=False)
    image2 = db.Column(db.String(255), nullable=True)
    image3 = db.Column(db.String(255), nullable=True)
    image4 = db.Column(db.String(255), nullable=True)

    rating = db.Column(db.Float, default=4.5)

    # Homepage section category (featured / bestseller)
    category = db.Column(db.String(50), default="featured", nullable=False)

    # Subcategory for filtering (men, women, shirts, jeans, etc.)
    subcategory = db.Column(db.String(100), nullable=True, default="")

    # ✅ FILTER FIELDS — comma-separated values
    # e.g. "S,M,L,XL,XXL" or "white,black,red"
    sizes = db.Column(db.String(255), nullable=True, default="")
    colors = db.Column(db.String(255), nullable=True, default="")

    # Optional — brand name for filtering
    brand = db.Column(db.String(100), nullable=True, default="Zenith")

    stock = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    order_items = db.relationship(
        "OrderItem",
        back_populates="product",
        lazy="dynamic"
    )

    reviews = db.relationship(
        "Review",
        back_populates="product",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    # ✅ PERFORMANCE INDEXES
    __table_args__ = (
        db.Index("idx_product_is_active", "is_active"),
        db.Index("idx_product_category", "category"),
        db.Index("idx_product_subcategory", "subcategory"),
        db.Index("idx_product_created_at", "created_at"),
        db.Index("idx_product_price", "price"),
    )

    @property
    def images(self):
        """Return list of all non-null images"""
        imgs = [self.image]
        for img in [self.image2, self.image3, self.image4]:
            if img:
                imgs.append(img)
        return imgs

    @property
    def size_list(self):
        """Return list of sizes from comma-separated string"""
        if not self.sizes:
            return []
        return [s.strip() for s in self.sizes.split(",") if s.strip()]

    @property
    def color_list(self):
        """Return list of colors from comma-separated string"""
        if not self.colors:
            return []
        return [c.strip() for c in self.colors.split(",") if c.strip()]

    @property
    def review_count(self):
        """Count of approved reviews"""
        try:
            return Review.query.filter_by(
                product_id=self.id,
                is_approved=True
            ).count()
        except Exception:
            return 0

    @property
    def avg_rating(self):
        """Average of approved reviews (falls back to self.rating)"""
        try:
            reviews = Review.query.filter_by(
                product_id=self.id,
                is_approved=True
            ).all()
            if reviews:
                return round(sum(r.rating for r in reviews) / len(reviews), 1)
            return self.rating or 0
        except Exception:
            return self.rating or 0

    @property
    def discount_percent(self):
        """Calculate discount % if old_price exists"""
        if self.old_price and self.old_price > self.price:
            return round(((self.old_price - self.price) / self.old_price) * 100)
        return 0

    def __repr__(self):
        return f"<Product {self.name}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description or "",
            "price": self.price,
            "old_price": self.old_price,
            "image": self.image,
            "image2": self.image2,
            "image3": self.image3,
            "image4": self.image4,
            "images": self.images,
            "rating": self.rating,
            "avg_rating": self.avg_rating,
            "review_count": self.review_count,
            "discount_percent": self.discount_percent,
            "category": self.category,
            "subcategory": self.subcategory or "",
            "sizes": self.sizes or "",
            "colors": self.colors or "",
            "size_list": self.size_list,
            "color_list": self.color_list,
            "brand": self.brand or "Zenith",
            "stock": self.stock,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================================================
# ORDER MODEL
# ==================================================

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)

    status = db.Column(db.String(50), default="pending")
    payment_method = db.Column(db.String(50), default="cod")
    payment_status = db.Column(db.String(50), default="pending")

    payment_id = db.Column(db.String(255), nullable=True)
    razorpay_order_id = db.Column(db.String(255), nullable=True)

    shipping_address = db.Column(db.Text, nullable=True)

    # ✅ COUPON FIELDS
    coupon_code = db.Column(db.String(50), nullable=True)
    discount_amount = db.Column(db.Float, default=0)

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )

    # ✅ PERFORMANCE INDEXES
    __table_args__ = (
        db.Index("idx_order_user_id", "user_id"),
        db.Index("idx_order_status", "status"),
        db.Index("idx_order_payment_status", "payment_status"),
        db.Index("idx_order_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Order #{self.id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "total_amount": self.total_amount,
            "status": self.status,
            "payment_method": self.payment_method,
            "payment_status": self.payment_status,
            "shipping_address": self.shipping_address,
            "coupon_code": self.coupon_code,
            "discount_amount": self.discount_amount,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================================================
# ORDER ITEM MODEL
# ==================================================

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)

    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False, default=0)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    size = db.Column(db.String(20), nullable=True)
    color = db.Column(db.String(50), nullable=True)

    # Relationships
    order = db.relationship("Order", back_populates="items")
    product = db.relationship("Product", back_populates="order_items")

    # ✅ PERFORMANCE INDEXES
    __table_args__ = (
        db.Index("idx_orderitem_order_id", "order_id"),
        db.Index("idx_orderitem_product_id", "product_id"),
    )

    def __repr__(self):
        return f"<OrderItem #{self.id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "price": self.price,
            "quantity": self.quantity,
            "size": self.size,
            "color": self.color,
        }


# ==================================================
# COUPON MODEL
# ==================================================

class Coupon(db.Model):
    __tablename__ = "coupons"

    id = db.Column(db.Integer, primary_key=True)

    code = db.Column(db.String(50), unique=True, nullable=False, index=True)

    # Discount as percentage (e.g., 20 = 20% off)
    discount_percent = db.Column(db.Integer, nullable=False)

    # Minimum order amount required (0 = no minimum)
    min_order_amount = db.Column(db.Float, default=0)

    # Maximum discount cap in ₹ (None = no cap)
    max_discount = db.Column(db.Float, nullable=True)

    # Expiry date (None = never expires)
    expiry_date = db.Column(db.DateTime, nullable=True)

    # Total usage limit (None = unlimited)
    usage_limit = db.Column(db.Integer, nullable=True)

    # How many times used
    used_count = db.Column(db.Integer, default=0)

    # Active / Inactive
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    # ✅ PERFORMANCE INDEXES
    __table_args__ = (
        db.Index("idx_coupon_is_active", "is_active"),
        db.Index("idx_coupon_expiry", "expiry_date"),
    )

    def __repr__(self):
        return f"<Coupon {self.code} - {self.discount_percent}%>"

    @property
    def is_expired(self):
        """Check if coupon is expired"""
        if not self.expiry_date:
            return False
        now = utc_now()
        expiry = self.expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        return expiry < now

    @property
    def is_exhausted(self):
        """Check if usage limit reached"""
        if not self.usage_limit:
            return False
        return self.used_count >= self.usage_limit

    @property
    def is_valid(self):
        """Full validity check"""
        return self.is_active and not self.is_expired and not self.is_exhausted

    def calculate_discount(self, order_amount):
        """
        Calculate discount for given order amount.
        Returns (discount_amount, error_message)
        """
        if not self.is_active:
            return 0, "This coupon is no longer active."

        if self.is_expired:
            return 0, "This coupon has expired."

        if self.is_exhausted:
            return 0, "This coupon has reached its usage limit."

        if order_amount < self.min_order_amount:
            return 0, f"Minimum order of ₹{int(self.min_order_amount)} required."

        # Calculate discount
        discount = (order_amount * self.discount_percent) / 100

        # Apply max discount cap
        if self.max_discount and discount > self.max_discount:
            discount = self.max_discount

        return round(discount, 2), None

    def to_dict(self):
        return {
            "id": self.id,
            "code": self.code,
            "discount_percent": self.discount_percent,
            "min_order_amount": self.min_order_amount,
            "max_discount": self.max_discount,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "usage_limit": self.usage_limit,
            "used_count": self.used_count,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "is_expired": self.is_expired,
            "is_exhausted": self.is_exhausted,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ==================================================
# REVIEW MODEL
# ==================================================

class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)

    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)

    # Review content
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(150), nullable=True)
    comment = db.Column(db.Text, nullable=False)

    # Optional photo (Cloudinary URL or local)
    photo_url = db.Column(db.String(500), nullable=True)

    # Moderation
    is_approved = db.Column(db.Boolean, default=False)
    is_verified_purchase = db.Column(db.Boolean, default=False)

    # Bonus — helpful votes
    helpful_count = db.Column(db.Integer, default=0)

    # Timestamps
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = db.relationship("User", back_populates="reviews")
    product = db.relationship("Product", back_populates="reviews")

    # ✅ PERFORMANCE INDEXES + CONSTRAINT
    __table_args__ = (
        db.UniqueConstraint("user_id", "product_id", name="unique_user_product_review"),
        db.Index("idx_review_product", "product_id"),
        db.Index("idx_review_user", "user_id"),
        db.Index("idx_review_approved", "is_approved"),
        db.Index("idx_review_created", "created_at"),
    )

    def __repr__(self):
        return f"<Review #{self.id} - {self.rating}★ for Product {self.product_id}>"

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "order_id": self.order_id,
            "rating": self.rating,
            "title": self.title or "",
            "comment": self.comment,
            "photo_url": self.photo_url,
            "is_approved": self.is_approved,
            "is_verified_purchase": self.is_verified_purchase,
            "helpful_count": self.helpful_count or 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_name": self.user.full_name if self.user else "Anonymous",
            "user_avatar": (
                self.user.full_name[0].upper()
                if self.user and self.user.full_name
                else "?"
            ),
        }