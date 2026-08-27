"""Real transactional email delivery via the Brevo API.

This is a genuine HTTP integration, not a mock: when EMAIL_PROVIDER_ENABLED
is true and BREVO_API_KEY is set, `send_email` makes a real POST to
https://api.brevo.com/v3/smtp/email and returns Brevo's own message id and
delivery outcome. When the provider is disabled (the default), nothing is
sent and the caller is told so explicitly - the app never claims an email
was sent when it wasn't, matching the project's standing rule against fake
"sent" confirmations (see docs/KNOWN_LIMITATIONS.md "External providers").

Brevo note: EMAIL_FROM_EMAIL must be verified as a sender in the Brevo
dashboard (Settings -> Senders) before this can send anything - unlike some
providers, Brevo has no shared sandbox sender to fall back to, so a send
attempt from an unverified address fails outright with a 4xx.
"""
import logging

import httpx

from app.core.config import get_settings

logger = logging.getLogger("rockstar_organics")
settings = get_settings()

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailResult:
    def __init__(self, sent: bool, provider_message_id: str | None = None, error: str | None = None):
        self.sent = sent
        self.provider_message_id = provider_message_id
        self.error = error


def send_email(*, to: str, subject: str, html: str, text: str) -> EmailResult:
    """Sends one transactional email. Returns an EmailResult describing what
    actually happened - never raises for a provider-side failure (a bad
    recipient, an unverified sender, etc.), so a failed email never breaks
    the request that triggered it (registration, password reset, ...); the
    caller decides how to surface EmailResult.sent == False."""
    if not settings.EMAIL_PROVIDER_ENABLED or not settings.BREVO_API_KEY or not settings.EMAIL_FROM_EMAIL:
        logger.info('{"message": "email provider disabled - not sending", "to": "%s", "subject": "%s"}', to, subject)
        return EmailResult(sent=False, error="Email provider is not configured.")

    try:
        response = httpx.post(
            BREVO_API_URL,
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "sender": {"name": settings.EMAIL_FROM_NAME, "email": settings.EMAIL_FROM_EMAIL},
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": html,
                "textContent": text,
            },
            timeout=10.0,
        )
        if response.status_code >= 400:
            logger.warning(
                '{"message": "email send failed", "to": "%s", "status": %s, "body": %s}',
                to, response.status_code, response.text[:500],
            )
            return EmailResult(sent=False, error=f"Brevo returned {response.status_code}: {response.text[:300]}")
        data = response.json()
        logger.info('{"message": "email sent", "to": "%s", "provider_id": "%s"}', to, data.get("messageId"))
        return EmailResult(sent=True, provider_message_id=data.get("messageId"))
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
