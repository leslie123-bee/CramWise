# Blunts brute-force / credential-stuffing attempts against the login and
# register endpoints - the two routes that don't require a token, so
# they're the ones an attacker could hammer with guesses.
from ..utils.rate_limit import RateLimiter

# 10 attempts per minute per IP address is generous for a real person
# (including a mistyped password or two) but slows down automated guessing.
_auth_limiter = RateLimiter(max_attempts=10, window_seconds=60)


def rate_limit_auth(req, res, next_):
    key = req.ip or 'unknown'
    if not _auth_limiter.allow(key):
        res.status(429).json({'error': 'Too many attempts from this address - wait a minute and try again'})
        return
    next_()
