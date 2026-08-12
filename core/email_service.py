"""
Email service for VeltrixSync
HTML email templates styled to match the VeltrixSync brand.
"""

import random
import resend
from django.conf import settings
from django.utils import timezone
from django.utils.html import escape, linebreaks
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
    """Send an HTML email via Resend API."""
    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.DEFAULT_FROM_EMAIL,
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        })
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
        <div class="header-logo">Veltrix<span>Sync</span></div>
        <div class="header-tagline">Copy Trading Platform</div>
        <div class="header-divider"></div>
    </div>
    """


# Platform key -> (glyph shown in the badge, brand color). Order controls display order.
_SOCIAL_META = {
    "facebook":  ("f",  "#1877F2"),
    "twitter":   ("X",  "#000000"),
    "instagram": ("IG", "#E1306C"),
    "linkedin":  ("in", "#0A66C2"),
    "telegram":  ("TG", "#26A5E4"),
    "youtube":   ("YT", "#FF0000"),
}
_SOCIAL_LABELS = {
    "facebook": "Facebook", "twitter": "Twitter / X", "instagram": "Instagram",
    "linkedin": "LinkedIn", "telegram": "Telegram", "youtube": "YouTube",
}


def _social_icons_html(social_links: dict | None) -> str:
    """
    Row of circular social icon badges for the footer. A platform is only
    rendered if `social_links` has a non-empty URL for it — e.g. passing
    {"facebook": "https://facebook.com/x"} renders just the Facebook icon.
    Returns "" (no row at all) when no links are provided.
    """
    if not social_links:
        return ""

    cells = []
    for key, (glyph, color) in _SOCIAL_META.items():
        url = (social_links.get(key) or "").strip()
        if not url:
            continue
        label = _SOCIAL_LABELS[key]
        cells.append(f"""
            <td style="padding:0 5px;">
                <a href="{escape(url)}" title="{label}" style="display:inline-block; width:32px; height:32px;
                   line-height:32px; background-color:{color}; border-radius:50%; text-align:center;
                   text-decoration:none; color:#ffffff; font-size:12px; font-weight:700;
                   font-family:Arial,Helvetica,sans-serif;">{glyph}</a>
            </td>""")

    if not cells:
        return ""

    return f"""
    <table role="presentation" align="center" cellpadding="0" cellspacing="0" border="0" style="margin:18px auto 4px;">
        <tr>{''.join(cells)}</tr>
    </table>
    """


def _footer_html(user_email: str, social_links: dict | None = None) -> str:
    frontend    = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    year        = timezone.now().year
    social_html = _social_icons_html(social_links)
    return f"""
    <div class="footer">
        <div class="footer-brand">VeltrixSync</div>
        <div class="footer-text">
            This is an automated message. Please do not reply directly to this email.
        </div>
        {social_html}
        <div class="footer-links">
            <a href="{frontend}/privacy">Privacy Policy</a>
            <a href="{frontend}/terms">Terms of Service</a>
            <a href="{frontend}/support">Support</a>
        </div>
        <div class="footer-text" style="margin-top:14px;">
            Sent to {user_email} &middot; &copy; {year} VeltrixSync. All rights reserved.
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
        <div class="heading">Welcome to VeltrixSync</div>
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
    return send_email(user.email, "Welcome to VeltrixSync", _wrap(body))


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
            To complete your VeltrixSync registration, enter the code below.
            It expires in <strong>10 minutes</strong>.
        </div>
        <div class="code-container">
            <div class="code-value">{code}</div>
            <div class="code-label">Email Verification Code</div>
        </div>
        <div class="notice">
            <p><strong>Security reminder:</strong> Never share this code with anyone.
            VeltrixSync will never ask for your code via phone or live chat.</p>
        </div>
        <div class="divider"></div>
        <div class="text" style="font-size:13px; color:#8fa896;">
            If you did not create a VeltrixSync account, you can safely ignore this email.
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Verify your email — VeltrixSync", _wrap(body))


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
    return send_email(user.email, "Login verification — VeltrixSync", _wrap(body))


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
            We received a request to reset the password for your VeltrixSync account.
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
    return send_email(user.email, "Password reset — VeltrixSync", _wrap(body))


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
            This is a confirmation that the password for your VeltrixSync account was
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
    return send_email(user.email, "Password changed — VeltrixSync", _wrap(body))


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
    subject = f"[VeltrixSync] Payment Intent — {user.email} — ${dollar_amount}"
    return send_email(admin_email, subject, _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: deposit notification
# ─────────────────────────────────────────────────────────────────────────────

def send_admin_deposit_notification(user, transaction) -> bool:
    admin_email = getattr(settings, "ADMIN_NOTIFICATION_EMAIL", settings.EMAIL_HOST_USER)
    now = timezone.now().strftime("%b %d, %Y at %I:%M %p UTC")
    tx_date = transaction.created_at.strftime("%b %d, %Y at %I:%M %p UTC")

    # Format crypto units — strip trailing zeros, keep meaning
    units_val = float(transaction.units or 0)
    amount_usd_val = float(transaction.amount_usd or 0)
    if units_val > 0 and abs(units_val - amount_usd_val) > 0.0001:
        units_display = f"{units_val:.8f}".rstrip("0").rstrip(".")
        crypto_row = f'<tr><td class="label">Crypto Amount</td><td class="value" style="font-weight:700;font-size:15px;color:#16a34a;">{units_display} {transaction.asset}</td></tr>'
    else:
        crypto_row = ""

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div style="margin-bottom:18px;"><span class="badge badge-pending">Pending Approval</span></div>
        <div class="heading">New Deposit Request</div>
        <div class="text">A deposit request has been submitted and requires your review.</div>
        <div class="amount-box deposit">
            <div class="amount">${transaction.amount_usd:,.2f}</div>
            <div class="amount-label">USD Amount</div>
        </div>
        <div class="section-title">Transaction Details</div>
        <table class="detail-table">
            <tr><td class="label">Reference</td><td class="value" style="font-size:12px;font-family:monospace;">{transaction.tx_id}</td></tr>
            <tr><td class="label">USD Amount</td><td class="value">${transaction.amount_usd:,.2f}</td></tr>
            {crypto_row}
            <tr><td class="label">Asset</td><td class="value">{transaction.asset}</td></tr>
            <tr><td class="label">Status</td><td class="value"><span class="badge badge-pending">PENDING</span></td></tr>
            <tr><td class="label">Date</td><td class="value">{tx_date}</td></tr>
        </table>
        <div class="section-title">User Information</div>
        <table class="detail-table">
            <tr><td class="label">Name</td><td class="value">{user.first_name} {user.last_name}</td></tr>
            <tr><td class="label">Email</td><td class="value">{user.email}</td></tr>
            <tr><td class="label">User ID</td><td class="value">#{user.id}</td></tr>
            <tr><td class="label">Balance</td><td class="value">${user.balance:,.2f}</td></tr>
        </table>
    </div>
    <div class="footer">
        <div class="footer-text">Admin notification &middot; Action required &middot; {now}</div>
    </div>
    """
    units_str = f"{units_val:.8f}".rstrip("0").rstrip(".") if units_val > 0 and abs(units_val - amount_usd_val) > 0.0001 else str(transaction.amount_usd)
    subject = f"[VeltrixSync] Deposit — {user.email} — ${transaction.amount_usd:,.2f} ({units_str} {transaction.asset})"
    return send_email(admin_email, subject, _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: withdrawal notification
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# User: deposit confirmation
# ─────────────────────────────────────────────────────────────────────────────

def send_user_deposit_confirmation(user, transaction, wallet_name: str = "") -> bool:
    name     = user.first_name or user.username or "Trader"
    tx_date  = transaction.created_at.strftime("%b %d, %Y at %I:%M %p UTC")
    asset_label = transaction.asset + (f" ({wallet_name})" if wallet_name else "")
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Deposit Request Received</div>
        <div class="text">
            We've received your deposit request and it is now under review.
            You will be notified once it has been approved and credited to your account.
        </div>
        <div class="amount-box deposit">
            <div class="amount">${transaction.amount_usd}</div>
            <div class="amount-label">Deposit Amount (USD)</div>
        </div>
        <div class="section-title">Request Details</div>
        <table class="detail-table">
            <tr>
                <td class="label">Reference</td>
                <td class="value" style="font-size:12px;font-family:monospace;">{transaction.tx_id}</td>
            </tr>
            <tr><td class="label">Asset</td><td class="value">{asset_label}</td></tr>
            <tr>
                <td class="label">Status</td>
                <td class="value"><span class="badge badge-pending">Pending</span></td>
            </tr>
            <tr><td class="label">Date</td><td class="value">{tx_date}</td></tr>
        </table>
        <div class="notice">
            <p>Deposits are typically reviewed within <strong>24–48 hours</strong>.
            If you have any questions, please contact our support team.</p>
        </div>
        <div style="text-align:center; margin:28px 0;">
            <a href="{frontend}/transactions" class="btn">View Transaction</a>
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Deposit Request Received — VeltrixSync", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# User: withdrawal confirmation
# ─────────────────────────────────────────────────────────────────────────────

def send_user_withdrawal_confirmation(user, transaction, wallet_name: str = "") -> bool:
    name     = user.first_name or user.username or "Trader"
    tx_date  = transaction.created_at.strftime("%b %d, %Y at %I:%M %p UTC")
    asset_label = transaction.asset + (f" ({wallet_name})" if wallet_name else "")
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    addr = transaction.wallet_address or ""
    masked_address = (addr[:6] + "..." + addr[-4:]) if len(addr) > 10 else addr

    destination_row = (
        f'<tr><td class="label">Destination</td>'
        f'<td class="value" style="font-size:12px;font-family:monospace;">{masked_address}</td></tr>'
        if masked_address else ""
    )

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Withdrawal Request Submitted</div>
        <div class="text">
            Your withdrawal request has been submitted and is pending approval.
            The requested amount has been reserved from your account balance.
        </div>
        <div class="amount-box withdraw">
            <div class="amount">${transaction.amount_usd}</div>
            <div class="amount-label">Withdrawal Amount (USD)</div>
        </div>
        <div class="section-title">Request Details</div>
        <table class="detail-table">
            <tr>
                <td class="label">Reference</td>
                <td class="value" style="font-size:12px;font-family:monospace;">{transaction.tx_id}</td>
            </tr>
            <tr><td class="label">Asset</td><td class="value">{asset_label}</td></tr>
            {destination_row}
            <tr>
                <td class="label">Status</td>
                <td class="value"><span class="badge badge-pending">Pending</span></td>
            </tr>
            <tr><td class="label">Date</td><td class="value">{tx_date}</td></tr>
        </table>
        <div class="notice">
            <p>Withdrawals are typically processed within <strong>24–48 hours</strong> after admin
            approval. If you did not initiate this request, please contact support immediately.</p>
        </div>
        <div style="text-align:center; margin:28px 0;">
            <a href="{frontend}/transactions" class="btn">View Transaction</a>
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Withdrawal Request Submitted — VeltrixSync", _wrap(body))


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
            <div class="amount">${transaction.amount_usd}</div>
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
    subject = f"[VeltrixSync] Withdrawal Request — {user.email} — ${transaction.amount_usd}"
    return send_email(admin_email, subject, _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# User: deposit approved
# ─────────────────────────────────────────────────────────────────────────────

def send_user_deposit_approved_email(user, transaction) -> bool:
    name     = user.first_name or user.username or "Trader"
    tx_date  = transaction.created_at.strftime("%b %d, %Y at %I:%M %p UTC")
    frontend = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        <div class="heading">Deposit Approved &amp; Credited</div>
        <div class="text">
            Great news! Your deposit has been reviewed and approved.
            The amount has been credited to your VeltrixSync account and is ready to use.
        </div>
        <div class="amount-box deposit">
            <div class="amount">${transaction.amount_usd:,.2f}</div>
            <div class="amount-label">Amount Credited (USD)</div>
        </div>
        <div class="section-title">Transaction Details</div>
        <table class="detail-table">
            <tr>
                <td class="label">Reference</td>
                <td class="value" style="font-size:12px;font-family:monospace;">{transaction.tx_id}</td>
            </tr>
            <tr><td class="label">Asset</td><td class="value">{transaction.asset}</td></tr>
            <tr>
                <td class="label">Status</td>
                <td class="value"><span class="badge badge-success">Completed</span></td>
            </tr>
            <tr><td class="label">Date</td><td class="value">{tx_date}</td></tr>
        </table>
        <div class="notice">
            <p>Your new account balance reflects this deposit. You can now use your funds to copy traders and grow your portfolio.</p>
        </div>
        <div style="text-align:center; margin:28px 0;">
            <a href="{frontend}/transactions" class="btn">View Transactions</a>
        </div>
    </div>
    {_footer_html(user.email)}
    """
    return send_email(user.email, "Deposit Approved — Funds Credited to Your Account", _wrap(body))


# ─────────────────────────────────────────────────────────────────────────────
# Admin: custom / bulk client email
# ─────────────────────────────────────────────────────────────────────────────
# Composed from the admin panel (dashboard app) and sent to one or many users
# at once. Reuses the exact same header/footer/button styling as every other
# email above — only the heading, message body, optional CTA button, and
# footer social icons change per campaign.
# ─────────────────────────────────────────────────────────────────────────────

def _build_custom_email_html(
    name: str,
    email: str,
    message: str,
    heading: str = "",
    social_links: dict | None = None,
    cta_text: str = "",
    cta_url: str = "",
) -> str:
    """
    Build the full HTML document for a custom email, shared by `send_custom_email`
    (real send) and `render_custom_email_preview` (admin preview, not sent).

    - `message` is plain text; blank lines start a new paragraph, single
      newlines become <br>. It is HTML-escaped, so admins can't break markup.
    - `heading` is optional — omitted entirely if blank.
    - `social_links` is an optional dict like {"facebook": "https://...", ...}.
      Only platforms with a non-empty URL get an icon; if none are set (or
      the dict is empty/None), no social row is rendered at all.
    - `cta_text` + `cta_url` are optional — both must be set to show a button.
    """
    message_html = linebreaks(message.strip(), autoescape=True)

    cta_block = ""
    if cta_text and cta_url:
        cta_block = f"""
        <div style="text-align:center; margin:32px 0;">
            <a href="{escape(cta_url)}" class="btn">{escape(cta_text)}</a>
        </div>"""

    heading_block = f'<div class="heading">{escape(heading)}</div>' if heading else ""

    body = f"""
    {_header_html()}
    <div class="body-content">
        <div class="greeting">Hello {name},</div>
        {heading_block}
        <div class="text">{message_html}</div>
        {cta_block}
    </div>
    {_footer_html(email, social_links)}
    """
    return _wrap(body)


def send_custom_email(
    user,
    subject: str,
    message: str,
    heading: str = "",
    social_links: dict | None = None,
    cta_text: str = "",
    cta_url: str = "",
) -> bool:
    """Send an admin-composed email to a single user using the VeltrixSync template."""
    name = user.first_name or user.username or "Trader"
    html = _build_custom_email_html(name, user.email, message, heading, social_links, cta_text, cta_url)
    return send_email(user.email, subject, html)


def render_custom_email_preview(
    message: str,
    heading: str = "",
    social_links: dict | None = None,
    cta_text: str = "",
    cta_url: str = "",
    preview_name: str = "Trader",
    preview_email: str = "client@example.com",
) -> str:
    """Render the exact HTML a recipient would receive, without sending — used for
    the admin panel's campaign detail/preview page."""
    return _build_custom_email_html(preview_name, preview_email, message, heading, social_links, cta_text, cta_url)
