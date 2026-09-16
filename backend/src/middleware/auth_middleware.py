import os
from ..utils.crypto_utils import verify_token


def authenticate(req, res, next_):
    header = req.headers.get('authorization', '')
    token = header[7:] if header.startswith('Bearer ') else None

    if not token:
        res.status(401).json({'error': 'Missing Authorization header (expected: Bearer <token>)'})
        return

    try:
        payload = verify_token(token, os.environ.get('JWT_SECRET', ''))
    except Exception:
        res.status(401).json({'error': 'Invalid or expired token'})
        return

    # next_() must run outside the try block - otherwise an HttpError
    # raised further down the chain (e.g. "Study group not found") gets
    # caught here and wrongly reported as an auth failure instead of
    # reaching http_kit's real error handler.
    req.user_id = payload.get('sub')
    next_()
