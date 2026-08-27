"""Password hashing and secure token utilities."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    try:
        return _hasher.verify(hashed, raw)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str, secret: str) -> str:
    return hmac.new(secret.encode(), token.encode(), hashlib.sha256).hexdigest()


PASSWORD_MIN_LENGTH = 10
# Argon2 hashing cost scales with input length; an unbounded password lets a
# client force expensive hashing on every login attempt (a cheap DoS lever).
# 256 characters is far beyond any real password while still generous.
PASSWORD_MAX_LENGTH = 256


def password_strength_errors(raw: str) -> list[str]:
    errors = []
    if len(raw) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(raw) > PASSWORD_MAX_LENGTH:
        errors.append(f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")
    if not any(c.isupper() for c in raw):
        errors.append("Password must include an uppercase letter.")
    if not any(c.islower() for c in raw):
        errors.append("Password must include a lowercase letter.")
    if not any(c.isdigit() for c in raw):
        errors.append("Password must include a digit.")
    return errors
