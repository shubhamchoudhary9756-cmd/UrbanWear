"""
Zenith - Database Models
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

    # ✅ NEW: Subcategory for filtering (men, women, shirts, jeans, etc.)
    subcategory = db.Column(db.String(100), nullable=True, default="")

    stock = db.Column(db.Integer, default=10)
    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    order_items = db.relationship(
        "OrderItem",
        back_populates="product",
        lazy="dynamic"
    )

    @property
    def images(self):
        """Return list of all non-null images"""
        imgs = [self.image]
        for img in [self.image2, self.image3, self.image4]:
            if img:
                imgs.append(img)
        return imgs

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
            "category": self.category,
            "subcategory": self.subcategory or "",  # ✅ NEW
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

    created_at = db.Column(db.DateTime, default=utc_now)

    # Relationships
    user = db.relationship("User", back_populates="orders")
    items = db.relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
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