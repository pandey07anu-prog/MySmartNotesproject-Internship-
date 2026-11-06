"""
Smart Notes Assistant - Email Dispatcher Service
Dispatches transactional emails via SMTP or safely logs in development mode.
"""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger("smart_notes.email")

# In-memory dev inbox for automated tests and local dev inspection
DEV_EMAIL_INBOX: List[Dict[str, Any]] = []


class EmailService:
    @staticmethod
    def is_smtp_configured() -> bool:
        return bool(settings.SMTP_HOST and settings.SMTP_USERNAME and settings.SMTP_PASSWORD)

    @classmethod
    def send_verification_email(cls, to_email: str, token: str) -> Dict[str, Any]:
        """Send account email verification link."""
        link = f"{settings.APP_BASE_URL}/#verify-email?token={token}"
        subject = "Verify your Smart Notes Assistant Account"
        text_content = f"Hello,\n\nPlease verify your Smart Notes Assistant account by visiting:\n{link}\n\nThis link will expire in 24 hours."
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #08090C; color: #F5F5F7; padding: 40px; border-radius: 12px; max-width: 520px; margin: auto;">
            <h2 style="color: #60A5FA; margin-bottom: 8px;">Smart Notes Assistant</h2>
            <p style="color: #989AA3; font-size: 14px; margin-top: 0;">Your thoughts, intelligently organized.</p>
            <hr style="border: none; border-top: 1px solid #1D2028; margin: 24px 0;" />
            <p style="font-size: 16px; line-height: 1.5;">Welcome! Please click the button below to verify your email address:</p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{link}" style="background-color: #2563EB; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 500; font-size: 15px; display: inline-block;">Verify Email Address</a>
            </div>
            <p style="color: #989AA3; font-size: 13px;">If you did not request this, you can safely ignore this email.</p>
            <p style="color: #64748B; font-size: 12px; word-break: break-all;">Direct link: {link}</p>
        </div>
        """

        if cls.is_smtp_configured():
            try:
                cls._dispatch_smtp(to_email, subject, text_content, html_content)
                logger.info(f"Verification email dispatched to {to_email} via SMTP.")
                return {"delivered": True, "channel": "smtp"}
            except Exception as e:
                logger.error(f"SMTP delivery failed: {e}. Falling back to dev record.")

        # Dev mode fallback
        record = {
            "to": to_email,
            "type": "verification",
            "token": token,
            "link": link,
            "subject": subject,
        }
        DEV_EMAIL_INBOX.append(record)
        logger.info(f"[DEV EMAIL] Verification email for {to_email}: {link}")
        return {
            "delivered": False,
            "channel": "dev_inbox",
            "link": link,
            "token": token,
            "message": "SMTP not configured; token available via development inbox."
        }

    @classmethod
    def send_password_reset_email(cls, to_email: str, token: str) -> Dict[str, Any]:
        """Send password reset token link."""
        link = f"{settings.APP_BASE_URL}/#reset-password?token={token}"
        subject = "Reset your Smart Notes Assistant Password"
        text_content = f"Hello,\n\nYou requested a password reset for your Smart Notes Assistant account.\nReset link: {link}\n\nThis link will expire in 1 hour."
        html_content = f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #08090C; color: #F5F5F7; padding: 40px; border-radius: 12px; max-width: 520px; margin: auto;">
            <h2 style="color: #60A5FA; margin-bottom: 8px;">Smart Notes Assistant</h2>
            <p style="color: #989AA3; font-size: 14px; margin-top: 0;">Password Reset Request</p>
            <hr style="border: none; border-top: 1px solid #1D2028; margin: 24px 0;" />
            <p style="font-size: 16px; line-height: 1.5;">Click below to set a new password for your account:</p>
            <div style="text-align: center; margin: 32px 0;">
                <a href="{link}" style="background-color: #2563EB; color: #ffffff; text-decoration: none; padding: 12px 28px; border-radius: 8px; font-weight: 500; font-size: 15px; display: inline-block;">Reset Password</a>
            </div>
            <p style="color: #989AA3; font-size: 13px;">If you did not request this, please disregard this email. Your password remains unchanged.</p>
            <p style="color: #64748B; font-size: 12px; word-break: break-all;">Direct link: {link}</p>
        </div>
        """

        if cls.is_smtp_configured():
            try:
                cls._dispatch_smtp(to_email, subject, text_content, html_content)
                logger.info(f"Password reset email dispatched to {to_email} via SMTP.")
                return {"delivered": True, "channel": "smtp"}
            except Exception as e:
                logger.error(f"SMTP delivery failed: {e}. Falling back to dev record.")

        # Dev mode fallback
        record = {
            "to": to_email,
            "type": "password_reset",
            "token": token,
            "link": link,
            "subject": subject,
        }
        DEV_EMAIL_INBOX.append(record)
        logger.info(f"[DEV EMAIL] Password reset email for {to_email}: {link}")
        return {
            "delivered": False,
            "channel": "dev_inbox",
            "link": link,
            "token": token,
            "message": "SMTP not configured; token available via development inbox."
        }

    @classmethod
    def _dispatch_smtp(cls, to_email: str, subject: str, text_content: str, html_content: str) -> None:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, [to_email], msg.as_string())


email_service = EmailService()

