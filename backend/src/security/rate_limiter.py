from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List
from fastapi import HTTPException, status
import threading

class LoginRateLimiter:
    """
    Sliding-window rate limiter for brute-force protection on authentication endpoints.
    Tracks failed attempts per IP address and email.
    """
    def __init__(self, max_attempts: int = 5, window_minutes: int = 15):
        self.max_attempts = max_attempts
        self.window = timedelta(minutes=window_minutes)
        self._attempts: Dict[str, List[datetime]] = defaultdict(list)
        self._lock = threading.Lock()

    def _cleanup_old_attempts(self, key: str, now: datetime) -> None:
        cutoff = now - self.window
        self._attempts[key] = [ts for ts in self._attempts[key] if ts > cutoff]

    def check_rate_limit(self, key: str) -> None:
        """Raise HTTP 429 if key has exceeded allowed failed attempts within window."""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_old_attempts(key, now)
            if len(self._attempts[key]) >= self.max_attempts:
                earliest = self._attempts[key][0]
                retry_after = int((earliest + self.window - now).total_seconds())
                retry_after = max(1, retry_after)
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Too many failed login attempts. Account temporarily locked for {retry_after} seconds.",
                    headers={"Retry-After": str(retry_after)}
                )

    def record_failed_attempt(self, key: str) -> None:
        """Record a failed login attempt."""
        now = datetime.now(timezone.utc)
        with self._lock:
            self._cleanup_old_attempts(key, now)
            self._attempts[key].append(now)

    def clear_failed_attempts(self, key: str) -> None:
        """Reset attempts upon successful authentication."""
        with self._lock:
            if key in self._attempts:
                del self._attempts[key]

# Global singleton
login_rate_limiter = LoginRateLimiter(max_attempts=5, window_minutes=15)
