"""
Email service for SignalSync
HTML email templates styled to match the SignalSync brand.
"""

import smtplib
import random
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Core send utility
# ─────────────────────────────────────────────────────────────────────────────

def generate_verification_code():
    """Generate a random 4-digit verification code."""
    return str(random.randint(1000, 9999))


def send_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send an HTML email via SMTP (TLS or SSL depending on settings)."""
    try:
        smtp_host     = settings.EMAIL_HOST
        smtp_port     = settings.EMAIL_PORT
        smtp_username = settings.EMAIL_HOST_USER
        smtp_password = settings.EMAIL_HOST_PASSWORD
        from_email    = settings.DEFAULT_FROM_EMAIL

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"]    = from_email
        message["To"]      = to_email
        message.attach(MIMEText(html_content, "html"))

        if settings.EMAIL_USE_TLS:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        else:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)

        server.login(smtp_username, smtp_password)
        server.sendmail(from_email, to_email, message.as_string())
        server.quit()

        logger.info(f"Email sent successfully to {to_email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {str(e)}")
        return False


def is_code_valid(user) -> bool:
    """Return True if the user's verification code is still within 10 minutes."""
    if not getattr(user, "code_created_at", None) or not getattr(user, "verification_code", None):
        return False
    return timezone.now() < user.code_created_at + timedelta(minutes=10)


# ─────────────────────────────────────────────────────────────────────────────
# Shared template helpers
# ─────────────────────────────────────────────────────────────────────────────
#
# Brand palette (mirrors frontend CSS tokens):
#   --background      : #0b1c11   (dark green page bg)
#   --card            : #132b1a   (card bg)
#   --card-border     : #1e3827
#   --primary         : #B0D45A   (lime green)
#   --foreground      : #f0f0f0
#   --muted-foreground: #8fa896
#   --profit          : #22c55e
#   --loss            : #f87171
#
# Emails are rendered on white backgrounds for universal client compat,
# but use the brand header + lime green accent throughout.
# ─────────────────────────────────────────────────────────────────────────────

def _base_styles() -> str:
    return """
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto,
                         'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1a1a1a;
            margin: 0;
            padding: 0;
            background-color: #f0f2f0;
            -webkit-font-smoothing: antialiased;
        }
        .wrapper {
            max-width: 600px;
            margin: 40px auto;
            background-color: #ffffff;
            border-radius: 6px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.10);
        }

        /* ── Header ── */
        .header {
            background-color: #0b1c11;
            padding: 32px 40px 28px;
        }
        .header-logo {
            font-size: 21px;
            font-weight: 800;
            color: #ffffff;
            letter-spacing: -0.3px;
        }
        .header-logo span {
            color: #B0D45A;
        }
        .header-tagline {
            font-size: 11px;
            color: #8fa896;
            margin-top: 4px;
            letter-spacing: 0.6px;
            text-transform: uppercase;
        }
        .header-divider {
            width: 36px;
            height: 2px;
            background-color: #B0D45A;
            margin-top: 18px;
        }

        /* ── Body ── */
        .body-content {
            padding: 40px;
        }
        .greeting {
            font-size: 14px;
            color: #6b7c6b;
            margin-bottom: 20px;
        }
        .heading {
            font-size: 22px;
            font-weight: 700;
            color: #0b1c11;
            margin-bottom: 14px;
            line-height: 1.3;
        }
        .text {
            font-size: 14px;
            color: #4b5c4b;
            margin-bottom: 22px;
            line-height: 1.75;
        }
        .divider {
            height: 1px;
            background-color: #e4ede4;
            margin: 30px 0;
        }

        /* ── CTA button ── */
        .btn {
            display: inline-block;
            padding: 13px 36px;
            background-color: #B0D45A;
            color: #0b1c11;
            text-decoration: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 700;
            letter-spacing: 0.2px;
        }

        /* ── Info box (lime accent) ── */
        .info-box {
            background-color: #f3f9e6;
            border-left: 3px solid #B0D45A;
            padding: 16px 20px;
            margin: 22px 0;
            border-radius: 0 4px 4px 0;
        }
        .info-box p {
            font-size: 13px;
            color: #3a4a2a;
            margin: 4px 0;
        }

        /* ── OTP / code block ── */
        .code-container {
            background-color: #0b1c11;
            border-radius: 8px;
            padding: 30px;
            margin: 28px 0;
            text-align: center;
        }
        .code-value {
            font-size: 44px;
            font-weight: 800;
            color: #B0D45A;
            letter-spacing: 14px;
            font-family: 'SF Mono', 'Fira Code', 'Courier New', monospace;
        }
        .code-label {
            font-size: 11px;
            color: #8fa896;
            margin-top: 10px;
            text-transform: uppercase;
            letter-spacing: 1.2px;
        }

        /* ── Warning notice (amber) ── */
        .notice {
            background-color: #fffbeb;
            border-left: 3px solid #f59e0b;
            padding: 14px 18px;
            margin: 22px 0;
            border-radius: 0 4px 4px 0;
        }
        .notice p {
            font-size: 13px;
            color: #78400a;
            margin: 0;
        }

        /* ── Detail table ── */
        .section-title {
            font-size: 11px;
            font-weight: 700;
            color: #8fa896;
            text-transform: uppercase;
            letter-spacing: 1.1px;
            margin-bottom: 10px;
            margin-top: 26px;
        }
        .detail-table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
        }
        .detail-table td {
            padding: 10px 0;
            font-size: 13px;
            border-bottom: 1px solid #edf3ed;
        }
        .detail-table .label {
            color: #8fa896;
            width: 40%;
            font-weight: 500;
        }
        .detail-table .value {
            color: #1a2a1a;
            font-weight: 600;
            text-align: right;
        }

        /* ── Status badges ── */
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .badge-pending  { background-color: #fef3c7; color: #92400e; }
        .badge-approved { background-color: #dcfce7; color: #14532d; }
        .badge-urgent   { background-color: #fee2e2; color: #991b1b; }
        .badge-info     { background-color: #e8f5d0; color: #3a6010; }

        /* ── Amount display ── */
        .amount-box {
            border-radius: 8px;
            padding: 26px;
            text-align: center;
            margin: 24px 0;
        }
        .amount-box .amount {
            font-size: 34px;
            font-weight: 800;
        }
        .amount-box .amount-label {
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 6px;
        }
        .amount-box.deposit  { background-color: #f0fdf4; border: 1px solid #bbf7d0; }
        .amount-box.deposit  .amount { color: #16a34a; }
        .amount-box.deposit  .amount-label { color: #4b7a4b; }
        .amount-box.withdraw { background-color: #fef2f2; border: 1px solid #fecaca; }
        .amount-box.withdraw .amount { color: #dc2626; }
        .amount-box.withdraw .amount-label { color: #7a3a3a; }
        .amount-box.neutral  { background-color: #f3f9e6; border: 1px solid #c8e886; }
        .amount-box.neutral  .amount { color: #4a7a10; }
        .amount-box.neutral  .amount-label { color: #4a6a10; }

        /* ── Link fallback ── */
        .link-fallback {
            background-color: #f4f9f4;
            border: 1px solid #d4e8d4;
            border-radius: 4px;
            padding: 12px 16px;
            margin: 18px 0;
            word-break: break-all;
            font-size: 12px;
            color: #4b6b4b;
            font-family: monospace;
        }

        /* ── Footer ── */
        .footer {
            background-color: #0d2016;
            padding: 26px 40px;
        }
        .footer-text {
            font-size: 12px;
            color: #5a7a5a;
            line-height: 1.65;
        }
        .footer-links {
            margin-top: 10px;
        }
        .footer-links a {
            color: #8fa896;
            text-decoration: none;
            font-size: 12px;
            margin-right: 16px;
        }
        .footer-brand {
            font-size: 13px;
            font-weight: 700;
            color: #B0D45A;
            margin-bottom: 6px;
        }
    """


def _header_html() -> str:
    return """
    <div class="header">
        <div class="header-logo">Signal<span>Sync</span></div>
        <div class="header-tagline">Copy Trading Platform</div>
        <div class="header-divider"></div>
    </div>
    """


def _footer_html(user_email: str) -> str:
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    year     = timezone.now().year
    return f"""
    <div class="footer">
        <div class="footer-brand">SignalSync</div>
        <div class="footer-text">
            This is an automated message. Please do not reply directly to this email.
        </div>
        <div class="footer-links">
            <a href="{frontend}/privacy">Privacy Policy</a>
            <a href="{frontend}/terms">Terms of Service</a>
            <a href="{frontend}/support">Support</a>
        </div>
        <div class="footer-text" style="margin-top:14px;">
            Sent to {user_email} &middot; &copy; {year} SignalSync. All rights reserved.
        </div>
    </div>
    """


def _wrap(body: str) -> str:
    """Wrap body HTML in a full document with shared styles."""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>{_base_styles()}</style>
</head>
<body>
    <div class="wrapper">
        {body}
    </div>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Welcome email
# ─────────────────────────────────────────────────────────────────────────────

def send_welcome_email(user) -> bool:
    name = user.first_name or user.username or "Trader"
    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Welcome to SignalSync</div>
        <div class="text">
            Your account has been successfully created. You're now part of a community of
            traders who copy the best-performing experts and grow together.
        </div>
        <div class="info-box">
            <p><strong>Get started in 3 steps:</strong></p>
            <p>1. Complete your profile and set your preferences</p>
            <p>2. Fund your account using your preferred method</p>
            <p>3. Browse top traders and start copy trading</p>
        </div>
        <div style="text-align:center; margin:32px 0;">
            <a href="{getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')}/dashboard" class="btn">
                Go to Dashboard
            </a>
        </div>
        <div class="divider"></div>
        <div class="text" style="font-size:13px; color:#8fa896;">
            If you have any questions, our support team is here to help around the clock.
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Welcome to SignalSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Email verification (OTP code)
# ─────────────────────────────────────────────────────────────────────────────

def send_verification_code_email(user, code: str) -> bool:
    name = user.first_name or user.username or "Trader"
    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Verify your email address</div>
        <div class="text">
            To complete your SignalSync registration, enter the code below.
            It expires in <strong>10 minutes</strong>.
        </div>
        <div class="code-container">
            <div class="code-value">{code}</div>
            <div class="code-label">Email Verification Code</div>
        </div>
        <div class="notice">
            <p><strong>Security reminder:</strong> Never share this code with anyone.
            SignalSync will never ask for your code via phone or live chat.</p>
        </div>
        <div class="divider"></div>
        <div class="text" style="font-size:13px; color:#8fa896;">
            If you did not create a SignalSync account, you can safely ignore this email.
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Verify your email — SignalSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Two-factor authentication code
# ─────────────────────────────────────────────────────────────────────────────

def send_2fa_code_email(user, code: str) -> bool:
    name = user.first_name or user.username or "Trader"
    now  = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")
    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Two-factor authentication</div>
        <div class="text">
            A sign-in attempt was detected on your account. Enter the code below to
            complete authentication. This code expires in <strong>10 minutes</strong>.
        </div>
        <div class="code-container">
            <div class="code-value">{code}</div>
            <div class="code-label">Authentication Code</div>
        </div>
        <table class="detail-table" style="margin-top:0;">
            <tr>
                <td class="label">Account</td>
                <td class="value">{user.email}</td>
            </tr>
            <tr>
                <td class="label">Timestamp</td>
                <td class="value">{now}</td>
            </tr>
        </table>
        <div class="notice">
            <p><strong>Unrecognised activity?</strong> If you did not attempt to sign in,
            change your password immediately and contact support.</p>
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Login verification — SignalSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Password reset
# ─────────────────────────────────────────────────────────────────────────────

def send_password_reset_email(user, token: str, uid: str) -> bool:
    frontend   = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    reset_link = f"{frontend}/reset-password?uid={uid}&token={token}"
    name       = user.first_name or user.username or "Trader"

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Reset your password</div>
        <div class="text">
            We received a request to reset the password for your SignalSync account.
            Click the button below to choose a new password. This link expires in
            <strong>1 hour</strong>.
        </div>
        <div style="text-align:center; margin:32px 0;">
            <a href="{reset_link}" class="btn">Reset Password</a>
        </div>
        <div class="text" style="font-size:13px; color:#8fa896;">
            If the button doesn't work, copy and paste the link below into your browser:
        </div>
        <div class="link-fallback">{reset_link}</div>
        <div class="notice">
            <p><strong>Didn't request this?</strong> If you did not initiate a password
            reset, no action is needed. Your current password remains unchanged.</p>
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Password reset — SignalSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Password changed confirmation
# ─────────────────────────────────────────────────────────────────────────────

def send_password_changed_email(user) -> bool:
    name = user.first_name or user.username or "Trader"
    now  = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
  
    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Your password has been changed</div>
        <div class="text">
            This is a confirmation that the password for your SignalSync account was
            successfully updated on <strong>{now}</strong>.
        </div>
        <div class="notice">
            <p><strong>Wasn't you?</strong> If you did not make this change, please
            <a href="{frontend}/support" style="color:#B0D45A;">contact support</a>
            immediately to secure your account.</p>
        </div>
        <div class="divider"></div>
        <div class="text" style="font-size:13px; color:#8fa896;">
            All previously active sessions have been invalidated. Sign in again with
            your new password.
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Password changed — SignalSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: payment intent notification
# ─────────────────────────────────────────────────────────────────────────────

def send_admin_payment_intent_notification(user, currency: str, dollar_amount, currency_unit) -> bool:
    admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", settings.EMAIL_HOST_USER)
    now = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div style="margin-bottom:18px;"><span class="badge badge-info">Payment Intent</span></div>
        <div class="heading">Deposit Intent Received</div>
        <div class="text">
            A user has entered an amount and is proceeding to the payment step.
            Follow up if no confirmed deposit is received.
        </div>
        <div class="amount-box neutral">
            <div class="amount">${dollar_amount}</div>
            <div class="amount-label">{currency_unit} {currency}</div>
        </div>
        <div class="section-title">Intent Details</div>
        <table class="detail-table">
            <tr><td class="label">Currency</td><td class="value">{currency}</td></tr>
            <tr><td class="label">USD Amount</td><td class="value">${dollar_amount}</td></tr>
            <tr><td class="label">Crypto Amount</td><td class="value">{currency_unit}</td></tr>
            <tr><td class="label">Timestamp</td><td class="value">{now}</td></tr>
        </table>
        <div class="section-title">User Information</div>
        <table class="detail-table">
            <tr><td class="label">Name</td><td class="value">{user.first_name} {user.last_name}</td></tr>
            <tr><td class="label">Email</td><td class="value">{user.email}</td></tr>
            <tr><td class="label">User ID</td><td class="value">#{user.id}</td></tr>
            <tr><td class="label">Balance</td><td class="value">${user.balance}</td></tr>
            <tr><td class="label">Is Trader</td><td class="value">{'Yes' if user.is_trader else 'No'}</td></tr>
        </table>
        <div class="notice">
            <p><strong>Note:</strong> This is a payment intent notification, not a confirmed deposit.
            Staff should follow up if no deposit is received within a reasonable time.</p>
        </div>
    </div>
    <div class="footer">
        <div class="footer-text">Admin notification &middot; Payment Intent &middot; {now}</div>
    </div>
    """
    subject = f"[SignalSync] Payment Intent — {user.email} — ${dollar_amount}"
    return send_email(admin_email, subject, _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: deposit notification
# ─────────────────────────────────────────────────────────────────────────────

def send_admin_deposit_notification(user, transaction) -> bool:
    admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", settings.EMAIL_HOST_USER)
    now = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")

    receipt_row = ""
    if getattr(transaction, "receipt", None):
        receipt_row = f"""
        <tr>
            <td class="label">Receipt</td>
            <td class="value">
                <a href="{transaction.receipt.url}" target="_blank"
                   style="color:#B0D45A; text-decoration:none;">View Receipt ↗</a>
            </td>
        </tr>"""

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div style="margin-bottom:18px;"><span class="badge badge-pending">Pending Approval</span></div>
        <div class="heading">New Deposit Request</div>
        <div class="text">A deposit request has been submitted and requires review.</div>
        <div class="amount-box deposit">
            <div class="amount">${transaction.amount}</div>
            <div class="amount-label">{getattr(transaction, 'unit', '')} {getattr(transaction, 'currency', '')}</div>
        </div>
        <div class="section-title">Transaction Details</div>
        <table class="detail-table">
            <tr><td class="label">Reference</td><td class="value">{getattr(transaction, 'reference', '—')}</td></tr>
            <tr><td class="label">Status</td><td class="value">{str(getattr(transaction, 'status', '—')).upper()}</td></tr>
            <tr><td class="label">Date</td><td class="value">{transaction.created_at.strftime('%b %d, %Y at %I:%M %p UTC') if hasattr(transaction, 'created_at') else now}</td></tr>
            {receipt_row}
        </table>
        <div class="section-title">User Information</div>
        <table class="detail-table">
            <tr><td class="label">Name</td><td class="value">{user.first_name} {user.last_name}</td></tr>
            <tr><td class="label">Email</td><td class="value">{user.email}</td></tr>
            <tr><td class="label">User ID</td><td class="value">#{user.id}</td></tr>
            <tr><td class="label">Balance</td><td class="value">${user.balance}</td></tr>
        </table>
    </div>
    <div class="footer">
        <div class="footer-text">Admin notification &middot; Action required &middot; {now}</div>
    </div>
    """
    subject = f"[SignalSync] Deposit Request — {user.email} — ${transaction.amount}"
    return send_email(admin_email, subject, _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: withdrawal notification
# ─────────────────────────────────────────────────────────────────────────────

def send_admin_withdrawal_notification(user, transaction, payment_method=None) -> bool:
    admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", settings.EMAIL_HOST_USER)
    now = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")

    method_type    = getattr(payment_method, "method_type", "Not specified") if payment_method else "Not specified"
    payment_address = "N/A"
    if payment_method:
        payment_address = (
            getattr(payment_method, "address", None)
            or getattr(payment_method, "bank_account_number", None)
            or "N/A"
        )

    bank_row = ""
    if payment_method and getattr(payment_method, "bank_name", None):
        bank_row = f"<tr><td class='label'>Bank</td><td class='value'>{payment_method.bank_name}</td></tr>"

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div style="margin-bottom:18px;"><span class="badge badge-urgent">Urgent — Approval Required</span></div>
        <div class="heading">Withdrawal Request</div>
        <div class="text">
            A withdrawal request has been submitted and requires immediate processing.
        </div>
        <div class="amount-box withdraw">
            <div class="amount">${transaction.amount}</div>
            <div class="amount-label">Withdrawal Amount</div>
        </div>
        <div class="notice">
            <p><strong>Note:</strong> The user's balance has already been deducted.
            Process this withdrawal promptly or refund the user if unable to complete.</p>
        </div>
        <div class="section-title">Transaction Details</div>
        <table class="detail-table">
            <tr><td class="label">Reference</td><td class="value">{getattr(transaction, 'reference', '—')}</td></tr>
            <tr><td class="label">Status</td><td class="value">{str(getattr(transaction, 'status', '—')).upper()}</td></tr>
            <tr><td class="label">Date</td><td class="value">{transaction.created_at.strftime('%b %d, %Y at %I:%M %p UTC') if hasattr(transaction, 'created_at') else now}</td></tr>
        </table>
        <div class="section-title">Payment Destination</div>
        <table class="detail-table">
            <tr><td class="label">Method</td><td class="value">{method_type}</td></tr>
            <tr><td class="label">Address / Account</td><td class="value" style="font-size:12px;">{payment_address}</td></tr>
            {bank_row}
        </table>
        <div class="section-title">User Information</div>
        <table class="detail-table">
            <tr><td class="label">Name</td><td class="value">{user.first_name} {user.last_name}</td></tr>
            <tr><td class="label">Email</td><td class="value">{user.email}</td></tr>
            <tr><td class="label">User ID</td><td class="value">#{user.id}</td></tr>
            <tr><td class="label">Remaining Balance</td><td class="value">${user.balance}</td></tr>
        </table>
    </div>
    <div class="footer">
        <div class="footer-text">Admin notification &middot; Urgent action required &middot; {now}</div>
    </div>
    """
    subject = f"[SignalSync] Withdrawal Request — {user.email} — ${transaction.amount}"
    return send_email(admin_email, subject, _wrap(body))
