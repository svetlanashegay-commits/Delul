import hashlib
import hmac
import secrets

from argon2 import PasswordHasher, Type
from argon2.exceptions import InvalidHashError, VerificationError

hasher = PasswordHasher(type=Type.ID)


def hash_password(password: str) -> str:
    return hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    if encoded.startswith("pbkdf2_sha256$"):
        # Compatibility with accounts registered before lesson 9.
        try:
            _, rounds, salt, expected = encoded.split("$")
            if int(rounds) != 600_000:
                return False
            actual = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode(),
                bytes.fromhex(salt),
                int(rounds),
            )
            return hmac.compare_digest(actual.hex(), expected)
        except (ValueError, TypeError):
            return False
    try:
        return hasher.verify(encoded, password)
    except (InvalidHashError, VerificationError):
        return False


def needs_rehash(encoded: str) -> bool:
    if not encoded.startswith("$argon2id$"):
        return True
    return hasher.check_needs_rehash(encoded)


DUMMY_HASH = hash_password(secrets.token_urlsafe(32))
