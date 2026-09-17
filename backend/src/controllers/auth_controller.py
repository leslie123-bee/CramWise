import json
import os
import threading
import time
import uuid

from ..config.db import db
from ..utils.crypto_utils import generate_numeric_code, hash_password, sign_token, verify_password
from ..utils.email_utils import send_reset_code_email, send_welcome_email
from ..utils.validators import is_non_empty_string, is_valid_email, within_max_length

THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000
RESET_CODE_TTL_MS = 15 * 60 * 1000
# Generic on purpose: never reveals whether an email address has an
# account (see forgot_password below).
_FORGOT_PASSWORD_GENERIC_MESSAGE = 'If an account exists for that email, a reset code has been sent to it.'


def register(req, res, next_):
    body = req.body or {}
    name, email, password = body.get('name'), body.get('email'), body.get('password')

    if not is_non_empty_string(name) or not is_non_empty_string(email) or not is_non_empty_string(password):
        return res.status(400).json({'error': 'name, email, and password are required'})
    if not within_max_length(name, 'name'):
        return res.status(400).json({'error': 'name is too long (100 characters max)'})
    if not is_valid_email(email):
        return res.status(400).json({'error': 'Enter a valid email address'})
    if len(password) < 8:
        return res.status(400).json({'error': 'Password must be at least 8 characters'})
    if not within_max_length(password, 'password'):
        return res.status(400).json({'error': 'Password is too long (256 characters max)'})

    normalized_email = email.lower().strip()
    if db.get('SELECT user_id FROM users WHERE email = ?', (normalized_email,)):
        return res.status(409).json({'error': 'An account with this email already exists'})

    user_id = str(uuid.uuid4())
    db.run(
        'INSERT INTO users (user_id, name, email, password_hash) VALUES (?, ?, ?, ?)',
        (user_id, name.strip(), normalized_email, hash_password(password)),
    )
    # Send the welcome email in the background so a slow or unreachable
    # mail server can never delay or block someone signing up.
    threading.Thread(target=send_welcome_email, args=(normalized_email, name.strip()), daemon=True).start()
    res.status(201).json({'token': _issue_token(user_id), 'user': public_user(get_user(user_id))})


def login(req, res, next_):
    body = req.body or {}
    email, password = body.get('email'), body.get('password')

    if not is_non_empty_string(email) or not is_non_empty_string(password):
        return res.status(400).json({'error': 'email and password are required'})
    if not within_max_length(password, 'password'):
        return res.status(401).json({'error': 'Invalid email or password'})

    user = db.get('SELECT * FROM users WHERE email = ?', (email.lower().strip(),))
    if not user or not verify_password(password, user['password_hash']):
        return res.status(401).json({'error': 'Invalid email or password'})

    res.json({'token': _issue_token(user['user_id']), 'user': public_user(user)})


def forgot_password(req, res, next_):
    body = req.body or {}
    email = body.get('email')

    if not is_non_empty_string(email):
        return res.status(400).json({'error': 'email is required'})

    user = db.get('SELECT user_id, name, email FROM users WHERE email = ?', (email.lower().strip(),))
    if user:
        code = generate_numeric_code(6)
        expires_at = str(int(time.time() * 1000) + RESET_CODE_TTL_MS)
        db.run(
            'UPDATE users SET reset_code_hash = ?, reset_code_expires_at = ? WHERE user_id = ?',
            (hash_password(code), expires_at, user['user_id']),
        )
        # Background thread: a slow mail server should never delay this
        # response (which must look identical whether or not the email
        # exists - see the generic message below).
        threading.Thread(
            target=send_reset_code_email, args=(user['email'], user['name'], code), daemon=True
        ).start()

    # Same response whether or not the account exists, so this endpoint
    # can't be used to check which emails are registered.
    res.json({'message': _FORGOT_PASSWORD_GENERIC_MESSAGE})


def reset_password(req, res, next_):
    body = req.body or {}
    email, code, new_password = body.get('email'), body.get('code'), body.get('new_password')

    if not is_non_empty_string(email) or not is_non_empty_string(code) or not is_non_empty_string(new_password):
        return res.status(400).json({'error': 'email, code, and new_password are required'})
    if len(new_password) < 8:
        return res.status(400).json({'error': 'Password must be at least 8 characters'})
    if not within_max_length(new_password, 'password'):
        return res.status(400).json({'error': 'Password is too long (256 characters max)'})

    user = db.get('SELECT * FROM users WHERE email = ?', (email.lower().strip(),))
    invalid = (
        not user
        or not user.get('reset_code_hash')
        or not user.get('reset_code_expires_at')
        or int(user['reset_code_expires_at']) < int(time.time() * 1000)
        or not verify_password(code.strip(), user['reset_code_hash'])
    )
    if invalid:
        return res.status(400).json({'error': 'That code is invalid or has expired - request a new one'})

    db.run(
        'UPDATE users SET password_hash = ?, reset_code_hash = NULL, reset_code_expires_at = NULL WHERE user_id = ?',
        (hash_password(new_password), user['user_id']),
    )
    res.json({'message': 'Password reset - you can now log in with your new password'})


def _issue_token(user_id):
    return sign_token({'sub': user_id}, os.environ.get('JWT_SECRET', ''), THIRTY_DAYS_MS)


def get_user(user_id):
    return db.get('SELECT * FROM users WHERE user_id = ?', (user_id,))


def public_user(user):
    if not user:
        return None
    user = dict(user)
    user.pop('password_hash', None)
    user.pop('reset_code_hash', None)
    user.pop('reset_code_expires_at', None)
    user['available_days'] = json.loads(user.get('available_days') or '[]')
    return user
