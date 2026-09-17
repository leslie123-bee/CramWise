# Sends account-related emails (a "your account was created" welcome
# email, and a "here's your password reset code" email) through a Gmail
# account, using Python's built-in smtplib - no extra package needed.
#
# Configuration (see .env.example): GMAIL_ADDRESS and GMAIL_APP_PASSWORD.
# If either is missing, email sending is silently skipped (a message is
# printed to the server log) rather than breaking sign-up - so the app
# keeps working even before email is set up, and keeps working if Gmail
# is briefly unreachable.

import os
import smtplib
import ssl
from email.message import EmailMessage

_SMTP_HOST = 'smtp.gmail.com'
_SMTP_PORT = 465


def _send(to_email, subject, body):
    address = os.environ.get('GMAIL_ADDRESS', '').strip()
    app_password = os.environ.get('GMAIL_APP_PASSWORD', '').strip()
    if not address or not app_password:
        print(f'Skipping email "{subject}" (GMAIL_ADDRESS / GMAIL_APP_PASSWORD not set)')
        return

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = address
    msg['To'] = to_email
    msg.set_content(body)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT, context=context) as server:
            server.login(address, app_password)
            server.send_message(msg)
        print(f'Email "{subject}" sent to {to_email}')
    except Exception as err:
        # Never let an email hiccup break the request that triggered it -
        # whatever it was for (account creation, a reset code) already
        # happened by the time this runs.
        print(f'Failed to send email "{subject}":', err)


def send_welcome_email(to_email, name):
    _send(
        to_email,
        'Your CramWise account is ready',
        f"Hi {name},\n\n"
        "Your CramWise account was created successfully. You can now sign in "
        "and start building your study plan.\n\n"
        "If you didn't create this account, you can ignore this email.\n\n"
        "- CramWise",
    )


def send_reset_code_email(to_email, name, code):
    _send(
        to_email,
        'Your CramWise password reset code',
        f"Hi {name},\n\n"
        f"Your CramWise password reset code is: {code}\n\n"
        "Enter this in the app to set a new password. This code expires in "
        "15 minutes.\n\n"
        "If you didn't ask to reset your password, you can ignore this "
        "email - your password will stay the same.\n\n"
        "- CramWise",
    )
