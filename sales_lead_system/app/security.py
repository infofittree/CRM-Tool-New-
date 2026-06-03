"""Password hashing helpers for Streamlit session authentication."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 250_000)
    return f"pbkdf2_sha256${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a PBKDF2 password hash."""
    try:
        algorithm, salt_b64, digest_b64 = password_hash.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = base64.b64decode(digest_b64)
        salt = base64.b64decode(salt_b64)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 250_000)
        return hmac.compare_digest(actual, expected)
    except ValueError:
        return False

