"""
Debug script for SMTP email issues
Run: python debug_email.py
"""

import os
import smtplib
import traceback
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("⚠️  python-dotenv not installed")


print("=" * 60)
print("EMAIL CONFIG CHECK")
print("=" * 60)

MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "").strip()
MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "").strip()
MAIL_SERVER = "smtp.gmail.com"
MAIL_PORT = 587

print(f"MAIL_SERVER:   {MAIL_SERVER}")
print(f"MAIL_PORT:     {MAIL_PORT}")
print(f"MAIL_USERNAME: {MAIL_USERNAME}")
print(f"MAIL_PASSWORD: {'*' * len(MAIL_PASSWORD)} (length: {len(MAIL_PASSWORD)})")

print()
print("=" * 60)
print("SMTP CONNECTION TEST")
print("=" * 60)

try:
    print("1️⃣  Connecting to Gmail SMTP...")
    server = smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=10)
    print("   ✅ Connected")

    print("2️⃣  Starting TLS...")
    server.starttls()
    print("   ✅ TLS started")

    print("3️⃣  Logging in with credentials...")
    server.login(MAIL_USERNAME, MAIL_PASSWORD)
    print("   ✅ Login successful")

    print("4️⃣  Sending test email...")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🧪 Zenith Debug — Test Email"
    msg["From"] = MAIL_USERNAME
    msg["To"] = MAIL_USERNAME

    text = "This is a test email from Zenith debug script."
    html = """
    <html><body style="font-family: Arial; padding: 20px;">
        <h2 style="color: #c9a961;">🧪 Debug Test Successful!</h2>
        <p>If you received this email, SMTP is working.</p>
        <p>Now order confirmation emails should also work.</p>
    </body></html>
    """

    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    server.send_message(msg)
    server.quit()
    print("   ✅ Test email sent successfully!")
    print()
    print("=" * 60)
    print("✅ ALL GOOD — SMTP working perfectly!")
    print("=" * 60)

except smtplib.SMTPAuthenticationError as e:
    print()
    print("=" * 60)
    print("❌ AUTHENTICATION FAILED")
    print("=" * 60)
    print(f"Error: {e}")
    print()
    print("POSSIBLE CAUSES:")
    print("  1. Gmail App Password wrong hai (16 chars, no spaces)")
    print("  2. MAIL_USERNAME .env mein galat hai")
    print("  3. 2-Step Verification ON nahi hai Gmail pe")
    print()
    print("FIX:")
    print("  1. Gmail → Account → Security → 2-Step Verification → ON")
    print("  2. Gmail → Account → Security → App Passwords")
    print("  3. 'Mail' app select karo → Generate")
    print("  4. 16-digit password copy karo (no spaces)")
    print("  5. .env mein paste karo: MAIL_PASSWORD=xxxxxxxxxxxxxxxx")

except smtplib.SMTPConnectError as e:
    print(f"❌ Connection error: {e}")

except smtplib.SMTPServerDisconnected as e:
    print(f"❌ Server disconnected: {e}")

except Exception as e:
    print(f"❌ Unexpected error: {e}")
    traceback.print_exc()
