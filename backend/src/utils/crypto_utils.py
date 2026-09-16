# Password hashing and login tokens, built entirely on Python's built-in
# hashlib/hmac modules - no `bcrypt` or `PyJWT` package required.
#
# Password hashing: scrypt (memory-hard, built into Python's hashlib since
# 3.6) with a random salt per password, stored as "salt:hash" in hex.
#
# Tokens: a minimal HMAC-signed token (same idea as a JWT - a payload plus
# a tamper-proof signature - just without the extra library). Swap this
# for the real `PyJWT` package later if you outgrow it; nothing else in
# the app needs to change, since auth_middleware.py and auth_controller.py
# only call the four functions exported here.
import base64
import hashlib
import hmac
import json
import os
import time

_SCRYPT_N = 16384
_SCRYPT_R = 8
_SCRYPT_P = 1
_KEY_LEN = 64


def hash_password(password):
    salt = os.urandom(16)
    derived = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_LEN)
    return f'{salt.hex()}:{derived.hex()}'


def verify_password(password, stored):
    try:
        salt_hex, hash_hex = str(stored).split(':')
    except ValueError:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    candidate = hashlib.scrypt(password.encode('utf-8'), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P, dklen=_KEY_LEN)
    return hmac.compare_digest(candidate, expected)


def _b64url_encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode('ascii')


def _b64url_decode(s):
    padding = '=' * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + padding)


def sign_token(payload, secret, ttl_ms):
    body = dict(payload)
    now_ms = int(time.time() * 1000)
    body['iat'] = now_ms
    body['exp'] = now_ms + ttl_ms
    payload_b64 = _b64url_encode(json.dumps(body).encode('utf-8'))
    signature = _b64url_encode(hmac.new(secret.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).digest())
    return f'{payload_b64}.{signature}'


def verify_token(token, secret):
    try:
        payload_b64, signature = str(token).split('.')
    except ValueError:
        raise ValueError('Malformed token')

    expected = _b64url_encode(hmac.new(secret.encode('utf-8'), payload_b64.encode('utf-8'), hashlib.sha256).digest())
    if not hmac.compare_digest(signature, expected):
        raise ValueError('Invalid token signature')

    payload = json.loads(_b64url_decode(payload_b64))
    if payload.get('exp', 0) < int(time.time() * 1000):
        raise ValueError('Token expired')
    return payload
