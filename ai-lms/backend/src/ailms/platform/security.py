"""Random tokens, one-time codes and their hashes."""

import hashlib
import hmac
import secrets

from ailms.platform.settings import get_settings


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    # The token is 256 random bits, so a plain hash is enough.
    return hashlib.sha256(token.encode()).hexdigest()


def new_login_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_login_code(email: str, code: str) -> str:
    # Keyed with the server secret: a copy of the table alone cannot be searched.
    key = get_settings().secret_key.encode()
    return hmac.new(key, f"{email}\n{code}".encode(), hashlib.sha256).hexdigest()


def same(a: str, b: str) -> bool:
    """Compare two secrets in constant time."""
    return hmac.compare_digest(a.encode(), b.encode())
