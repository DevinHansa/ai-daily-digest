"""
email_sender/sender.py — Sends the digest email via Gmail SMTP.
"""

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SL_TZ = timezone(timedelta(hours=5, minutes=30))


def send_digest(html_body: str, subject: str = None) -> bool:
    """
    Send the HTML digest email via Gmail SMTP.
    Returns True on success, False on failure.
    """
    sender    = os.environ.get("GMAIL_SENDER", "")
    password  = os.environ.get("GMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("DIGEST_RECIPIENT", "as2020323@sci.sjp.ac.lk")

    if not sender or not password:
        logger.error("[Email] GMAIL_SENDER and GMAIL_APP_PASSWORD must be set in .env!")
        return False

    if not subject:
        date_str = datetime.now(SL_TZ).strftime("%d %b %Y")
        subject = f"🧠 Your Daily AI Digest — {date_str}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AI News Digest <{sender}>"
    msg["To"]      = recipient

    # Plain text fallback
    plain = "Your AI News Digest is here. Please view this email in an HTML-capable client."
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        logger.info(f"[Email] Connecting to Gmail SMTP…")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender, password)
            server.sendmail(sender, recipient, msg.as_string())
        logger.info(f"[Email] ✅ Digest sent to {recipient}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "[Email] ❌ Authentication failed! Check GMAIL_SENDER and GMAIL_APP_PASSWORD.\n"
            "  → Make sure you're using a 16-character Google App Password, not your Gmail password.\n"
            "  → Go to: Google Account → Security → 2-Step Verification → App Passwords"
        )
        return False
    except Exception as e:
        logger.error(f"[Email] ❌ Failed to send email: {e}")
        return False
