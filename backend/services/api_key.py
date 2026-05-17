"""
Secure API key utilities — generate, hash, and verify API keys.

API keys are treated like passwords:
  - The plaintext key is shown to the user exactly once on generation.
  - Only a SHA-256 hash is stored in the database.
  - A short prefix (e.g. "mgpt_ab12…") is stored separately for display.
  - Verification hashes the incoming key and compares against the stored hash.

SHA-256 is appropriate here (vs bcrypt) because API keys are high-entropy
random strings that are not vulnerable to dictionary attacks.
"""

import hashlib
import secrets
from typing import Tuple

# Prefix all keys with this tag for easy identification
_KEY_TAG = "mgpt_"

# Number of hex chars from the raw key to store as a display prefix
_PREFIX_DISPLAY_LEN = 8


def generate_api_key() -> Tuple[str, str, str]:
    """
    Generate a new API key.

    Returns:
        (plaintext_key, key_hash, key_prefix)
        - plaintext_key: the full key to show to the user once (e.g. "mgpt_a1b2c3d4…")
        - key_hash:      SHA-256 hex digest to store in `User.api_key`
        - key_prefix:    short display prefix to store in `User.api_key_prefix`
    """
    raw = secrets.token_hex(24)  # 48 hex chars of entropy
    plaintext_key = f"{_KEY_TAG}{raw}"
    key_hash = hash_api_key(plaintext_key)
    key_prefix = f"{_KEY_TAG}{raw[:_PREFIX_DISPLAY_LEN]}…"
    return plaintext_key, key_hash, key_prefix


def hash_api_key(plaintext_key: str) -> str:
    """Return a deterministic SHA-256 hex digest of *plaintext_key*."""
    return hashlib.sha256(plaintext_key.encode("utf-8")).hexdigest()


def verify_api_key(plaintext_key: str, stored_hash: str) -> bool:
    """
    Constant-time comparison of a plaintext key against its stored hash.

    Uses `secrets.compare_digest` to prevent timing side-channels.
    """
    candidate = hash_api_key(plaintext_key)
    return secrets.compare_digest(candidate, stored_hash)
