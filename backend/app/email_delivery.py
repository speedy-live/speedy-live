"""SMTP delivery for customer email verification messages."""
from __future__ import annotations

import smtplib
from email.message import EmailMessage


class EmailDeliveryError(RuntimeError):
    pass


def send_customer_verification_email(*, host: str, port: int, username: str,
                                     password: str, sender: str, recipient: str,
                                     verification_url: str, use_starttls: bool = True) -> None:
    if not host or not sender or not recipient or not verification_url:
        raise EmailDeliveryError("Customer email delivery is not fully configured.")
    message = EmailMessage()
    message["Subject"] = "Verify your SPEEDY LIVE email address"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Welcome to SPEEDY LIVE.\n\n"
        "Verify your email address by opening this link:\n"
        f"{verification_url}\n\n"
        "This link expires in 30 minutes and can only be used once. "
        "If you did not create this account, you can ignore this email."
    )
    try:
        with smtplib.SMTP(host, port, timeout=15) as smtp:
            smtp.ehlo()
            if use_starttls:
                smtp.starttls()
                smtp.ehlo()
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise EmailDeliveryError("Could not deliver the customer verification email.") from exc
