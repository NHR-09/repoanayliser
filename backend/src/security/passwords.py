import hashlib
import hmac
import secrets
import re
from typing import Optional

# Current OWASP Password Storage Guidance recommends 600,000 iterations for PBKDF2-HMAC-SHA256
DEFAULT_ITERATIONS = 600_000
ALGORITHM = "pbkdf2_sha256"

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128

def validate_password_strength(password: str) -> Optional[str]:
    """
    Validate password strength against security best practices:
    - Minimum 8 characters, maximum 128 characters
    - At least one lowercase letter
    - At least one uppercase letter
    - At least one number
    - At least one special character
    Returns error string if invalid, or None if strong.
    """
    if not password or len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password cannot exceed {PASSWORD_MAX_LENGTH} characters."
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_+=\[\]\\/`~;']", password):
        return "Password must contain at least one special character."
    return None

def hash_password(password: str, iterations: int = DEFAULT_ITERATIONS) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256 with a random 16-byte salt
    and 600,000 iterations (OWASP current guidance).
    Returns string in format: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty")
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations
    )
    return f"{ALGORITHM}${iterations}${salt.hex()}${key.hex()}"

def verify_password(plain_password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored PBKDF2 hash using constant-time comparison.
    """
    if not plain_password or not stored_hash:
        return False
    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != ALGORITHM:
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        
        computed_key = hashlib.pbkdf2_hmac(
            "sha256",
            plain_password.encode("utf-8"),
            salt,
            iterations
        )
        return hmac.compare_digest(computed_key, expected_key)
    except Exception:
        return False
