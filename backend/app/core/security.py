"""Password hashing and secure token utilities."""
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

# A real Argon2 hash with no corresponding account, used solely to keep
# login's hash-verification cost constant whether or not the submitted
# email exists (see verify_password's docstring) - never used to
# authenticate anything.
DUMMY_PASSWORD_HASH = _hasher.hash("rockstar-organics-timing-safety-dummy-hash")


def hash_password(raw: str) -> str:
    return _hasher.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    """Always pass a real hash (DUMMY_PASSWORD_HASH when there is no real
    user) rather than skipping this call for a nonexistent account - Argon2
    verification is deliberately expensive, so skipping it only for
    nonexistent emails makes login's response time a timing side-channel
    that reveals which emails are registered."""
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


def verify_password_or_dummy(raw: str, hashed: str | None) -> bool:
    """For login: pass the real user's hash, or None if no such user. Either
    way this performs one real Argon2 verification, so response time
    doesn't leak whether the email is registered (see verify_password)."""
    return verify_password(raw, hashed if hashed is not None else DUMMY_PASSWORD_HASH)


def password_strength_errors(raw: str) -> list[str]:
    # Letter case is deliberately not enforced separately (no more "must
    # include an uppercase letter" / "must include a lowercase letter") -
    # an all-uppercase or all-lowercase password satisfies this just fine,
    # only a letter of either case plus a digit is required.
    errors = []
    if len(raw) < PASSWORD_MIN_LENGTH:
        errors.append(f"Password must be at least {PASSWORD_MIN_LENGTH} characters.")
    if len(raw) > PASSWORD_MAX_LENGTH:
        errors.append(f"Password must be at most {PASSWORD_MAX_LENGTH} characters.")
    if not any(c.isalpha() for c in raw):
        errors.append("Password must include a letter.")
    if not any(c.isdigit() for c in raw):
        errors.append("Password must include a digit.")
    return errors
