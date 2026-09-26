import hashlib
import hmac
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

password_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
DUMMY_PASSWORD_HASH = password_hasher.hash("NotARealPassword!123456")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def perform_dummy_password_check(password: str) -> None:
    verify_password(password, DUMMY_PASSWORD_HASH)


def generate_session_token() -> str:
    return secrets.token_hex(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def secure_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def email_fingerprint(email: str) -> str:
    return hashlib.sha256(normalize_email(email).encode("utf-8")).hexdigest()[:16]
