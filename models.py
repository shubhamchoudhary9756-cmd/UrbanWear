"""
Zenith - Database Models
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash, check_password_hash


db = SQLAlchemy()


def utc_now():
    """Timezone-aware UTC now (Python 3.12+ compatible)"""
    return datetime.now(timezone.utc)


# ==================================================
# USER MODEL
# ==================================================

class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(15), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)

    # Password reset fields
    reset_token = db.Column(db.String(100), unique=True, nullable=True, index=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)

    # Admin field
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    orders = db.relationship(
        "Order",
        backref="user",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, raw_password):
        """Hash and set password securely"""
        self.password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Verify password"""
        return check_password_hash(self.password, raw_password)


# ==================================================
# PRODUCT MODEL
# ==================================================

class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), unique=True, nullable=True)
    price = db.Column(db.Float, nullable=False)
    old_price = db.Column(db.Float, nullable=True)
    image = db.Column(db.String(300), nullable=False)
    image2 = db.Column(db.String(300), nullable=True)
    image3 = db.Column(db.String(300), nullable=True)
    image4 = db.Column(db.String(300), nullable=True)
    rating = db.Column(db.Float, default=4.5)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), default="featured", index=True)
    stock = db.Column(db.Integer, default=10, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=utc_now)

    def __repr__(self):
        return f"<Product {self.name}>"

    def to_dict(self):
        """Convert to dict (backward compatibility with templates)"""
        images = [self.image]
        if self.image2:
            images.append(self.image2)
        if self.image3:
            images.append(self.image3)
        if self.image4:
            images.append(self.image4)

        return {
            "id": self.id,
            "name": self.name,
            "price": self.price,
            "old_price": self.old_price or 0,
            "image": self.image,
            "images": images,
            "rating": self.rating,
            "description": self.description or "",
            "category": self.category,
            "stock": self.stock,
        }


# ==================================================
# ORDER MODEL
# ==================================================

class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default="pending", index=True)
    payment_method = db.Column(db.String(50), default="cod")
    shipping_address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)

    # Payment fields
    payment_id = db.Column(db.String(100), nullable=True)
    payment_status = db.Column(db.String(50), default="pending", index=True)
    razorpay_order_id = db.Column(db.String(100), nullable=True, index=True)

    # Relationships
    items = db.relationship(
        "OrderItem",
        backref="order",
        cascade="all, delete-orphan",
        lazy="joined"
    )

    def __repr__(self):
        return f"<Order #{self.id}>"


# ==================================================
# ORDER ITEM MODEL
# ==================================================

class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(
        db.Integer,
        db.ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    product_id = db.Column(db.Integer, nullable=False, index=True)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    size = db.Column(db.String(10), nullable=True)
    color = db.Column(db.String(50), nullable=True)

    def __repr__(self):
        return f"<OrderItem {self.product_name}>"

    @property
    def subtotal(self):
        return self.price * self.quantity