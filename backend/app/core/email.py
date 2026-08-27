"""Real transactional email delivery via the Resend API.

This is a genuine HTTP integration, not a mock: when EMAIL_PROVIDER_ENABLED
is true and RESEND_API_KEY is set, `send_email` makes a real POST to
https://api.resend.com/emails and returns Resend's own message id and
delivery outcome. When the provider is disabled (the default), nothing is
sent and the caller is told so explicitly - the app never claims an email
was sent when it wasn't, matching the project's standing rule against fake
"sent" confirmations (see docs/KNOWN_LIMITATIONS.md "External providers").

Resend note: an API key tied to an account with no verified sending
domain can only deliver to the account's own registered email address
(Resend's sandbox restriction) using the shared onboarding@resend.com
sender. Verify a domain in the Resend dashboard and set EMAIL_FROM_ADDRESS
to an address on it to send to arbitrary recipients.
"""
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("rockstar_organics")
settings = get_settings()

RESEND_API_URL = "https://api.resend.com/emails"


class EmailResult:
    def __init__(self, sent: bool, provider_message_id: str | None = None, error: str | None = None):
        self.sent = sent
        self.provider_message_id = provider_message_id
        self.error = error


def send_email(*, to: str, subject: str, html: str, text: str) -> EmailResult:
    """Sends one transactional email. Returns an EmailResult describing what
    actually happened - never raises for a provider-side failure (a bad
    recipient, an unverified domain, etc.), so a failed email never breaks
    the request that triggered it (registration, password reset, ...); the
    caller decides how to surface EmailResult.sent == False."""
    if not settings.EMAIL_PROVIDER_ENABLED or not settings.RESEND_API_KEY:
        logger.info('{"message": "email provider disabled - not sending", "to": "%s", "subject": "%s"}', to, subject)
        return EmailResult(sent=False, error="Email provider is not configured.")

    try:
        response = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": settings.EMAIL_FROM_ADDRESS,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
            },
            timeout=10.0,
        )
        if response.status_code >= 400:
            logger.warning(
                '{"message": "email send failed", "to": "%s", "status": %s, "body": %s}',
                to, response.status_code, response.text[:500],
            )
            return EmailResult(sent=False, error=f"Resend returned {response.status_code}: {response.text[:300]}")
        data = response.json()
        logger.info('{"message": "email sent", "to": "%s", "provider_id": "%s"}', to, data.get("id"))
        return EmailResult(sent=True, provider_message_id=data.get("id"))
    except httpx.HTTPError as exc:
        logger.warning('{"message": "email send raised an error", "to": "%s", "error": "%s"}', to, exc)
        return EmailResult(sent=False, error=str(exc))


def otp_email(code: str) -> tuple[str, str]:
    html = f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #2f5d34;">Rockstar Organics</h2>
      <p>Your verification code is:</p>
      <p style="font-size: 32px; font-weight: 700; letter-spacing: 6px; color: #1a1a1a;">{code}</p>
      <p>This code expires in {settings.OTP_TTL_MINUTES} minutes. If you did not request this, you can ignore this email.</p>
    </div>
    """
    text = f"Your Rockstar Organics verification code is {code}. It expires in {settings.OTP_TTL_MINUTES} minutes."
    return html, text


def password_reset_email(reset_url: str) -> tuple[str, str]:
    html = f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #2f5d34;">Rockstar Organics</h2>
      <p>We received a request to reset your password. Click the link below to choose a new one:</p>
      <p><a href="{reset_url}" style="color: #2f5d34;">{reset_url}</a></p>
      <p>This link expires in {settings.PASSWORD_RESET_TOKEN_TTL_MINUTES} minutes. If you did not request this, you can ignore this email - your password will not change.</p>
    </div>
    """
    text = f"Reset your Rockstar Organics password: {reset_url} (expires in {settings.PASSWORD_RESET_TOKEN_TTL_MINUTES} minutes)"
    return html, text


def welcome_email(full_name: str, role_label: str) -> tuple[str, str]:
    html = f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #2f5d34;">Welcome to Rockstar Organics, {full_name}</h2>
      <p>Your {role_label} account is ready. You can sign in any time at {settings.PUBLIC_APP_URL}/login.</p>
    </div>
    """
    text = f"Welcome to Rockstar Organics, {full_name}. Your {role_label} account is ready. Sign in at {settings.PUBLIC_APP_URL}/login."
    return html, text


def application_approved_email(contact_person: str, business_name: str, login_email: str, temp_password: str, portal_label: str) -> tuple[str, str]:
    html = f"""
    <div style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 480px; margin: 0 auto;">
      <h2 style="color: #2f5d34;">Your {portal_label} application has been approved</h2>
      <p>Hello {contact_person},</p>
      <p><strong>{business_name}</strong> has been approved as a Rockstar Organics {portal_label.lower()}.</p>
      <p>Sign in at {settings.PUBLIC_APP_URL}/login with:</p>
      <p>Email: <strong>{login_email}</strong><br/>Temporary password: <strong>{temp_password}</strong></p>
      <p>You will be asked to set a new password on first sign-in.</p>
    </div>
    """
    text = (
        f"Your {portal_label} application for {business_name} has been approved. "
        f"Sign in at {settings.PUBLIC_APP_URL}/login with email {login_email} and temporary password {temp_password}. "
        "You will be asked to set a new password on first sign-in."
    )
    return html, text
