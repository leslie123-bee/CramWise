# A small in-memory rate limiter - no Redis, no extra package. Fine for a
# single-process server like this one; if this ever runs as multiple
# processes behind a load balancer, each process would track its own
# counts, which is a reasonable limitation to accept for now rather than
# add an external dependency for.
import threading
import time


class RateLimiter:
    def __init__(self, max_attempts, window_seconds):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits = {}  # key -> list of timestamps within the current window
        self._lock = threading.Lock()

    def allow(self, key):
        """True if this call is within the limit (and counts it); False if
        the key should be rejected."""
        now = time.time()
        with self._lock:
            recent = [t for t in self._hits.get(key, ()) if now - t < self.window_seconds]
            if len(recent) >= self.max_attempts:
                self._hits[key] = recent
                return False
            recent.append(now)
            self._hits[key] = recent
            return True
