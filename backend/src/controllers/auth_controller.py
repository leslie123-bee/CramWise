import json
import os
import uuid

from ..config.db import db
from ..utils.crypto_utils import hash_password, sign_token, verify_password
from ..utils.validators import is_non_empty_string, is_valid_email, within_max_length

THIRTY_DAYS_MS = 30 * 24 * 60 * 60 * 1000


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


def _issue_token(user_id):
    return sign_token({'sub': user_id}, os.environ.get('JWT_SECRET', ''), THIRTY_DAYS_MS)


def get_user(user_id):
    return db.get('SELECT * FROM users WHERE user_id = ?', (user_id,))


def public_user(user):
    if not user:
        return None
    user = dict(user)
    user.pop('password_hash', None)
    user['available_days'] = json.loads(user.get('available_days') or '[]')
    return user
