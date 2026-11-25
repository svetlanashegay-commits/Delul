"""Compatibility imports; password implementation lives in core/passwords.py."""

from app.core.passwords import DUMMY_HASH, hash_password, verify_password

__all__ = ["DUMMY_HASH", "hash_password", "verify_password"]
