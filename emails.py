"""
Zenith — Email System
Order confirmations, payment receipts, status updates, welcome emails
"""

from flask import render_template_string, url_for
from flask_mail import Message
from datetime import datetime

# Ye import runtime pe inject honge (circular import avoid karne ke liye)
mail = None
app = None


def init_email(mail_instance, app_instance):
    """Initialize mail + app context (called from app.py)"""
    global mail, app
    mail = mail_instance
    app = app_instance


# ==================================================
# BASE EMAIL TEMPLATE
# ==================================================

def _base_template(content_html):
    """Wrap content in Zenith branded email template"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; background: #f5f1ea; font-family: Arial, sans-serif;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background: #f5f1ea; padding: 30px 15px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width: 600px; width: 100%; background: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">

                        <!-- HEADER -->
                        <tr>
                            <td style="background: #1a1a1a; padding: 35px 30px; text-align: center;">
                                <div style="font-family: Georgia, serif; font-size: 32px; font-weight: 600; color: #c9a961; letter-spacing: 8px; margin: 0; padding-left: 8px;">
                                    ZENITH
                                </div>
                                <div style="font-family: Arial, sans-serif; font-size: 10px; font-weight: 500; color: #c9a961; letter-spacing: 4px; margin-top: 8px; text-transform: uppercase; opacity: 0.85;">
                                    WEAR THE PEAK
                                </div>
                            </td>
                        </tr>

                        <!-- CONTENT -->
                        <tr>
                            <td style="padding: 40px 35px; background: #ffffff;">
                                {content_html}
                            </td>
                        </tr>

                        <!-- FOOTER -->
                        <tr>
                            <td style="background: #1a1a1a; padding: 30px 25px; text-align: center;">
                                <div style="color: #888; font-size: 11px; line-height: 1.8; font-family: Arial, sans-serif;">
                                    Questions? Reply to this email or contact us at
                                    <a href="mailto:support@zenith.com" style="color: #c9a961; text-decoration: none;">support@zenith.com</a>
                                </div>
                                <div style="margin-top: 18px; padding-top: 18px; border-top: 1px solid #2a2a2a;">
                                    <a href="#" style="display: inline-block; margin: 0 6px; color: #c9a961; text-decoration: none; font-size: 13px;">Instagram</a>
                                    <span style="color: #444;">•</span>
                                    <a href="#" style="display: inline-block; margin: 0 6px; color: #c9a961; text-decoration: none; font-size: 13px;">Facebook</a>
                                    <span style="color: #444;">•</span>
                                    <a href="#" style="display: inline-block; margin: 0 6px; color: #c9a961; text-decoration: none; font-size: 13px;">Twitter</a>
                                </div>
                                <div style="color: #555; font-size: 10px; margin-top: 20px; letter-spacing: 1px; font-family: Arial, sans-serif;">
                                    © {datetime.now().year} ZENITH. All rights reserved.
                                </div>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """


# ==================================================
# COMPONENTS
# ==================================================

def _order_summary_block(order):
    """Render order items + totals"""

    items_html = ""
    for item in order.items:
        item_total = (item.price or 0) * (item.quantity or 1)
        variant_text = ""
        if item.size or item.color:
            parts = []
            if item.size:
                parts.append(f"Size: {item.size}")
            if item.color:
                parts.append(f"Color: {item.color}")
            variant_text = f'<div style="font-size: 11px; color: #888; margin-top: 4px;">{" • ".join(parts)}</div>'

        items_html += f"""
        <tr>
            <td style="padding: 14px 0; border-bottom: 1px solid #f0ece6;">
                <div style="font-size: 14px; color: #1a1a1a; font-weight: 600; margin-bottom: 4px;">
                    {item.product_name}
                </div>
                {variant_text}
            </td>
            <td style="padding: 14px 0; border-bottom: 1px solid #f0ece6; text-align: center; font-size: 13px; color: #666; vertical-align: top;">
                ×{item.quantity}
            </td>
            <td style="padding: 14px 0; border-bottom: 1px solid #f0ece6; text-align: right; font-size: 14px; color: #1a1a1a; font-weight: 600; vertical-align: top;">
                ₹{int(item_total):,}
            </td>
        </tr>
        """

    # Discount row (only if applied)
    discount_row = ""
    if order.discount_amount and order.discount_amount > 0:
        discount_row = f"""
        <tr>
            <td colspan="2" style="padding: 10px 0; text-align: right; font-size: 13px; color: #28a745; font-weight: 600;">
                Discount ({order.coupon_code or "Coupon"})
            </td>
            <td style="padding: 10px 0; text-align: right; font-size: 14px; color: #28a745; font-weight: 700;">
                − ₹{int(order.discount_amount):,}
            </td>
        </tr>
        """

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 20px 0; border-collapse: collapse;">
        <thead>
            <tr>
                <th style="text-align: left; padding: 10px 0; font-size: 10px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; border-bottom: 2px solid #1a1a1a; font-weight: 700;">
                    Item
                </th>
                <th style="text-align: center; padding: 10px 0; font-size: 10px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; border-bottom: 2px solid #1a1a1a; font-weight: 700;">
                    Qty
                </th>
                <th style="text-align: right; padding: 10px 0; font-size: 10px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; border-bottom: 2px solid #1a1a1a; font-weight: 700;">
                    Price
                </th>
            </tr>
        </thead>
        <tbody>
            {items_html}
            {discount_row}
        </tbody>
        <tfoot>
            <tr>
                <td colspan="2" style="padding: 16px 0 0; text-align: right; font-size: 12px; color: #666; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 700; border-top: 2px solid #1a1a1a;">
                    Total
                </td>
                <td style="padding: 16px 0 0; text-align: right; font-size: 22px; color: #c9a961; font-weight: 700; border-top: 2px solid #1a1a1a;">
                    ₹{int(order.total_amount):,}
                </td>
            </tr>
        </tfoot>
    </table>
    """


def _cta_button(text, url):
    """Render primary CTA button"""
    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin: 25px 0;">
        <tr>
            <td align="center">
                <a href="{url}"
                   style="display: inline-block; padding: 15px 40px; background: #1a1a1a; color: #ffffff;
                          text-decoration: none; font-size: 12px; font-weight: 700;
                          letter-spacing: 2px; text-transform: uppercase; border-radius: 4px;">
                    {text}
                </a>
            </td>
        </tr>
    </table>
    """


def _order_status_badge(status):
    """Colored status badge"""
    colors = {
        "pending":    ("#fff8e6", "#856404"),
        "processing": ("#e6f4f9", "#0c5460"),
        "shipped":    ("#e6f0ff", "#004085"),
        "delivered":  ("#eaf7ed", "#155724"),
        "cancelled":  ("#fdecee", "#721c24"),
    }
    bg, fg = colors.get(status.lower(), ("#f0f0f0", "#666"))
    return f"""
    <span style="display: inline-block; padding: 6px 14px; background: {bg}; color: {fg};
                 font-size: 11px; font-weight: 700; letter-spacing: 1.5px;
                 text-transform: uppercase; border-radius: 20px;">
        {status.upper()}
    </span>
    """


# ==================================================
# EMAIL 1 — ORDER PLACED (COD)
# ==================================================

def send_order_placed_email(order, user):
    """Send when COD order is placed"""
    if not mail or not app:
        return False

    try:
        with app.app_context():
            track_url = url_for("order_details", order_id=order.id, _external=True)

            content = f"""
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; width: 70px; height: 70px; background: #eaf7ed;
                                border-radius: 50%; line-height: 70px; font-size: 32px; margin-bottom: 15px;">
                        ✅
                    </div>
                    <h1 style="font-family: Georgia, serif; font-size: 26px; font-weight: 600;
                               color: #1a1a1a; margin: 0 0 10px; letter-spacing: -0.3px;">
                        Order Confirmed!
                    </h1>
                    <p style="font-size: 14px; color: #666; margin: 0; font-family: Arial, sans-serif;">
                        Thank you for shopping with Zenith
                    </p>
                </div>

                <p style="font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 20px;">
                    Hi <strong>{user.full_name}</strong>,
                </p>

                <p style="font-size: 15px; color: #555; line-height: 1.7; margin: 0 0 25px;">
                    We've received your order and will start processing it shortly.
                    You'll receive a shipping confirmation once it's dispatched.
                </p>

                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom: 10px;">
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Order Number
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 14px; font-weight: 700; color: #1a1a1a;">
                            #ZEN-{order.id:05d}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Order Date
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 13px; color: #1a1a1a;">
                            {order.created_at.strftime("%d %B %Y")}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Payment
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 13px; color: #1a1a1a;">
                            Cash on Delivery
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase; vertical-align: top;">
                            Status
                        </td>
                        <td style="padding: 8px 0; text-align: right;">
                            {_order_status_badge(order.status)}
                        </td>
                    </tr>
                </table>

                <div style="margin: 30px 0 10px; padding: 20px 0; border-top: 1px dashed #e0e0e0;">
                    <div style="font-size: 12px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 15px; font-weight: 700;">
                        Items Ordered
                    </div>
                    {_order_summary_block(order)}
                </div>

                <div style="margin: 25px 0; padding: 20px; background: #faf8f5; border-left: 3px solid #c9a961; border-radius: 2px;">
                    <div style="font-size: 11px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px; font-weight: 700;">
                        Shipping Address
                    </div>
                    <div style="font-size: 14px; color: #333; line-height: 1.7; font-family: Arial, sans-serif;">
                        <strong>{user.full_name}</strong><br>
                        {order.shipping_address or "Address not provided"}
                    </div>
                </div>

                {_cta_button("View Order Details", track_url)}

                <p style="font-size: 13px; color: #888; text-align: center; margin: 25px 0 0; line-height: 1.6;">
                    Need help? Reply to this email and our team will assist you.
                </p>
            """

            msg = Message(
                subject=f"✅ Order Confirmed — #ZEN-{order.id:05d}",
                recipients=[user.email],
                html=_base_template(content)
            )
            mail.send(msg)
            print(f"✅ Order placed email sent to {user.email}")
            return True

    except Exception as e:
        print(f"❌ Order placed email error: {e}")
        return False


# ==================================================
# EMAIL 2 — PAYMENT SUCCESSFUL
# ==================================================

def send_payment_success_email(order, user):
    """Send when Razorpay payment is verified"""
    if not mail or not app:
        return False

    try:
        with app.app_context():
            track_url = url_for("order_details", order_id=order.id, _external=True)

            content = f"""
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; width: 70px; height: 70px; background: #eaf7ed;
                                border-radius: 50%; line-height: 70px; font-size: 32px; margin-bottom: 15px;">
                        💳
                    </div>
                    <h1 style="font-family: Georgia, serif; font-size: 26px; font-weight: 600;
                               color: #1a1a1a; margin: 0 0 10px;">
                        Payment Successful!
                    </h1>
                    <p style="font-size: 14px; color: #666; margin: 0;">
                        Your order is being processed
                    </p>
                </div>

                <p style="font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 20px;">
                    Hi <strong>{user.full_name}</strong>,
                </p>

                <p style="font-size: 15px; color: #555; line-height: 1.7; margin: 0 0 25px;">
                    We've received your payment of <strong style="color: #1a1a1a;">₹{int(order.total_amount):,}</strong>
                    for order <strong>#ZEN-{order.id:05d}</strong>. Your order is now being prepared for shipping.
                </p>

                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Order Number
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 14px; font-weight: 700; color: #1a1a1a;">
                            #ZEN-{order.id:05d}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Payment ID
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 13px; color: #1a1a1a; word-break: break-all;">
                            {order.payment_id or "N/A"}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Amount Paid
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 16px; font-weight: 700; color: #c9a961;">
                            ₹{int(order.total_amount):,}
                        </td>
                    </tr>
                </table>

                <div style="margin: 30px 0 10px; padding: 20px 0; border-top: 1px dashed #e0e0e0;">
                    <div style="font-size: 12px; color: #999; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 15px; font-weight: 700;">
                        Order Summary
                    </div>
                    {_order_summary_block(order)}
                </div>

                {_cta_button("Track Your Order", track_url)}

                <p style="font-size: 13px; color: #888; text-align: center; margin: 25px 0 0; line-height: 1.6;">
                    We'll notify you as soon as your order ships.
                </p>
            """

            msg = Message(
                subject=f"💳 Payment Received — #ZEN-{order.id:05d}",
                recipients=[user.email],
                html=_base_template(content)
            )
            mail.send(msg)
            print(f"✅ Payment success email sent to {user.email}")
            return True

    except Exception as e:
        print(f"❌ Payment success email error: {e}")
        return False


# ==================================================
# EMAIL 3 — ORDER CANCELLED
# ==================================================

def send_order_cancelled_email(order, user):
    """Send when order is cancelled (by user or admin)"""
    if not mail or not app:
        return False

    try:
        with app.app_context():
            shop_url = url_for("home", _external=True)

            content = f"""
                <div style="text-align: center; margin-bottom: 30px;">
                    <div style="display: inline-block; width: 70px; height: 70px; background: #fdecee;
                                border-radius: 50%; line-height: 70px; font-size: 32px; margin-bottom: 15px;">
                        ❌
                    </div>
                    <h1 style="font-family: Georgia, serif; font-size: 26px; font-weight: 600;
                               color: #1a1a1a; margin: 0 0 10px;">
                        Order Cancelled
                    </h1>
                    <p style="font-size: 14px; color: #666; margin: 0;">
                        Your order has been cancelled
                    </p>
                </div>

                <p style="font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 20px;">
                    Hi <strong>{user.full_name}</strong>,
                </p>

                <p style="font-size: 15px; color: #555; line-height: 1.7; margin: 0 0 25px;">
                    Your order <strong>#ZEN-{order.id:05d}</strong> has been cancelled.
                    {("A full refund of ₹" + str(int(order.total_amount)) + " will be processed within 5-7 business days.") if order.payment_status == "paid" else "No payment was charged for this order."}
                </p>

                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Cancelled Order
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 14px; font-weight: 700; color: #1a1a1a;">
                            #ZEN-{order.id:05d}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Order Total
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 15px; font-weight: 600; color: #1a1a1a;">
                            ₹{int(order.total_amount):,}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Cancellation Date
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 13px; color: #1a1a1a;">
                            {datetime.now().strftime("%d %B %Y")}
                        </td>
                    </tr>
                </table>

                <p style="font-size: 14px; color: #555; line-height: 1.7; margin: 30px 0 20px;">
                    Changed your mind? We'd love to have you back.
                </p>

                {_cta_button("Continue Shopping", shop_url)}

            """

            msg = Message(
                subject=f"Order Cancelled — #ZEN-{order.id:05d}",
                recipients=[user.email],
                html=_base_template(content)
            )
            mail.send(msg)
            print(f"✅ Order cancelled email sent to {user.email}")
            return True

    except Exception as e:
        print(f"❌ Order cancelled email error: {e}")
        return False


# ==================================================
# EMAIL 4 — ORDER STATUS UPDATE
# ==================================================

def send_status_update_email(order, user, old_status, new_status):
    """Send when admin updates order status"""
    if not mail or not app:
        return False

    # Skip email if no actual change
    if old_status == new_status:
        return False

    try:
        with app.app_context():
            track_url = url_for("order_details", order_id=order.id, _external=True)

            # Status-specific message
            status_messages = {
                "processing": ("Order Being Processed", "We're preparing your order for shipment."),
                "shipped":    ("Order Shipped! 🚚", "Your order is on its way. Track it with the link below."),
                "delivered":  ("Order Delivered! 🎉", "We hope you love your purchase. Leave a review!"),
                "cancelled":  ("Order Cancelled", "Your order has been cancelled."),
                "pending":    ("Order Received", "Your order is confirmed and pending processing."),
            }
            title, subtitle = status_messages.get(
                new_status.lower(),
                ("Order Status Updated", f"Your order status is now {new_status}.")
            )

            content = f"""
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="font-family: Georgia, serif; font-size: 26px; font-weight: 600;
                               color: #1a1a1a; margin: 0 0 10px;">
                        {title}
                    </h1>
                    <p style="font-size: 14px; color: #666; margin: 0;">
                        {subtitle}
                    </p>
                </div>

                <p style="font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 20px;">
                    Hi <strong>{user.full_name}</strong>,
                </p>

                <table width="100%" cellpadding="0" cellspacing="0" border="0">
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Order Number
                        </td>
                        <td style="padding: 8px 0; text-align: right; font-size: 14px; font-weight: 700; color: #1a1a1a;">
                            #ZEN-{order.id:05d}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            Previous Status
                        </td>
                        <td style="padding: 8px 0; text-align: right;">
                            {_order_status_badge(old_status)}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0; font-size: 12px; color: #888; letter-spacing: 1.5px; text-transform: uppercase;">
                            New Status
                        </td>
                        <td style="padding: 8px 0; text-align: right;">
                            {_order_status_badge(new_status)}
                        </td>
                    </tr>
                </table>

                <div style="margin: 30px 0 10px; padding: 20px 0; border-top: 1px dashed #e0e0e0;">
                    {_order_summary_block(order)}
                </div>

                {_cta_button("View Order", track_url)}

            """

            msg = Message(
                subject=f"Order Update — #ZEN-{order.id:05d} is now {new_status}",
                recipients=[user.email],
                html=_base_template(content)
            )
            mail.send(msg)
            print(f"✅ Status update email sent to {user.email} ({old_status} → {new_status})")
            return True

    except Exception as e:
        print(f"❌ Status update email error: {e}")
        return False


# ==================================================
# EMAIL 5 — WELCOME EMAIL
# ==================================================

def send_welcome_email(user):
    """Send when user signs up"""
    if not mail or not app:
        return False

    try:
        with app.app_context():
            shop_url = url_for("home", _external=True)

            content = f"""
                <div style="text-align: center; margin-bottom: 30px;">
                    <h1 style="font-family: Georgia, serif; font-size: 28px; font-weight: 600;
                               color: #1a1a1a; margin: 0 0 10px; letter-spacing: -0.3px;">
                        Welcome to Zenith!
                    </h1>
                    <p style="font-size: 14px; color: #c9a961; margin: 0; letter-spacing: 2px; text-transform: uppercase; font-weight: 600;">
                        Wear The Peak
                    </p>
                </div>

                <p style="font-size: 15px; color: #333; line-height: 1.7; margin: 0 0 20px;">
                    Hi <strong>{user.full_name}</strong>,
                </p>

                <p style="font-size: 15px; color: #555; line-height: 1.7; margin: 0 0 25px;">
                    Welcome to the Zenith family. We craft premium fashion for those who
                    demand more from their wardrobe — timeless designs, exceptional quality,
                    and a commitment to style.
                </p>

                <div style="margin: 30px 0; padding: 25px; background: #faf8f5; border-radius: 4px; text-align: center;">
                    <div style="font-size: 12px; color: #999; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 10px; font-weight: 700;">
                        Your Welcome Gift
                    </div>
                    <div style="font-family: 'Courier New', monospace; font-size: 24px; font-weight: 700; color: #1a1a1a; letter-spacing: 4px; margin-bottom: 8px;">
                        WELCOME10
                    </div>
                    <div style="font-size: 13px; color: #28a745; font-weight: 600;">
                        10% OFF on your first order
                    </div>
                </div>

                {_cta_button("Start Shopping", shop_url)}

                <p style="font-size: 13px; color: #888; text-align: center; margin: 25px 0 0; line-height: 1.6;">
                    Follow us on social media for exclusive drops and offers.
                </p>
            """

            msg = Message(
                subject="🎉 Welcome to Zenith — Here's 10% Off",
                recipients=[user.email],
                html=_base_template(content)
            )
            mail.send(msg)
            print(f"✅ Welcome email sent to {user.email}")
            return True

    except Exception as e:
        print(f"❌ Welcome email error: {e}")
        return False