"""
Omura Life Manager — Security Utilities
=========================================
Encryption, hashing, JWT management, and OAuth token helpers used
throughout the Omura backend.

* **Data encryption** — Fernet symmetric encryption (AES-128-CBC under the
  hood with HMAC-SHA256 authentication) via the ``cryptography`` library.
* **Password hashing** — bcrypt through ``passlib``.
* **JWT tokens** — creation and validation via ``python-jose``.
* **OAuth token storage** — lightweight helpers that persist provider tokens
  to an encrypted on-disk JSON store.

Usage::

    from backend.app.utils.security import (
        encrypt_data, decrypt_data,
        hash_password, verify_password,
        create_jwt_token, decode_jwt_token,
        store_token, get_token,
    )
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from cryptography.fernet import Fernet, InvalidToken
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.app.config import settings

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_SECRET_KEY: str = settings.SECRET_KEY
_ENCRYPTION_KEY: str = settings.ENCRYPTION_KEY
_JWT_ALGORITHM: str = "HS256"
_JWT_DEFAULT_EXPIRE_MINUTES: int = 60  # 1 hour

# Directory used for persisting encrypted OAuth tokens.
_TOKEN_STORE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "tokens"

# ---------------------------------------------------------------------------
# Fernet cipher (derived from the configured encryption key)
# ---------------------------------------------------------------------------


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key suitable for Fernet.

    Fernet requires exactly 32 bytes, base64-encoded.  We use SHA-256 to
    normalise an arbitrary-length passphrase into the right size.
    """
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


_fernet = Fernet(_derive_fernet_key(_ENCRYPTION_KEY))

# ---------------------------------------------------------------------------
# Password hashing (bcrypt via passlib)
# ---------------------------------------------------------------------------
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ---------------------------------------------------------------------------
# Public API — Encryption
# ---------------------------------------------------------------------------


def encrypt_data(plaintext: str, key: Optional[str] = None) -> str:
    """Encrypt *plaintext* and return the ciphertext as a URL-safe string.

    Parameters
    ----------
    plaintext:
        The string to encrypt.
    key:
        Optional encryption key override.  When ``None`` the application-wide
        ``ENCRYPTION_KEY`` from settings is used.

    Returns
    -------
    str
        Fernet-encoded ciphertext (URL-safe base64).

    Raises
    ------
    ValueError
        If *plaintext* is empty.
    """
    if not plaintext:
        raise ValueError("plaintext must not be empty")

    cipher = Fernet(_derive_fernet_key(key)) if key else _fernet
    return cipher.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_data(ciphertext: str, key: Optional[str] = None) -> str:
    """Decrypt a Fernet *ciphertext* and return the original plaintext.

    Parameters
    ----------
    ciphertext:
        The Fernet-encoded token string.
    key:
        Optional encryption key override.  When ``None`` the application-wide
        ``ENCRYPTION_KEY`` from settings is used.

    Returns
    -------
    str
        The decrypted plaintext.

    Raises
    ------
    cryptography.fernet.InvalidToken
        If the ciphertext is invalid or the key is wrong.
    ValueError
        If *ciphertext* is empty.
    """
    if not ciphertext:
        raise ValueError("ciphertext must not be empty")

    cipher = Fernet(_derive_fernet_key(key)) if key else _fernet
    return cipher.decrypt(ciphertext.encode("utf-8")).decode("utf-8")


# ---------------------------------------------------------------------------
# Public API — Password Hashing
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Return a bcrypt hash of *password*.

    Parameters
    ----------
    password:
        The plaintext password to hash.

    Returns
    -------
    str
        The bcrypt hash string (includes salt and cost factor).
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify *plain_password* against a previously hashed value.

    Parameters
    ----------
    plain_password:
        The candidate plaintext password.
    hashed_password:
        The stored bcrypt hash.

    Returns
    -------
    bool
        ``True`` if the password matches, ``False`` otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ---------------------------------------------------------------------------
# Public API — JWT Tokens
# ---------------------------------------------------------------------------


def create_jwt_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None,
    secret_key: Optional[str] = None,
) -> str:
    """Create a signed JWT token.

    Parameters
    ----------
    data:
        Payload claims to encode (e.g. ``{"sub": "user_id"}``).
    expires_delta:
        How long until the token expires.  Defaults to 60 minutes.
    secret_key:
        Signing key override.  Defaults to the application ``SECRET_KEY``.

    Returns
    -------
    str
        The encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=_JWT_DEFAULT_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(
        to_encode,
        secret_key or _SECRET_KEY,
        algorithm=_JWT_ALGORITHM,
    )


def decode_jwt_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Decode and validate a JWT token.

    Parameters
    ----------
    token:
        The encoded JWT string.
    secret_key:
        Signing key override.  Defaults to the application ``SECRET_KEY``.

    Returns
    -------
    dict
        The decoded payload.

    Raises
    ------
    jose.JWTError
        If the token is expired, tampered with, or otherwise invalid.
    """
    return jwt.decode(
        token,
        secret_key or _SECRET_KEY,
        algorithms=[_JWT_ALGORITHM],
    )


def validate_jwt_token(
    token: str,
    secret_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """Decode a JWT token, returning ``None`` instead of raising on failure.

    This is a convenience wrapper around :func:`decode_jwt_token` for code
    paths where an invalid token is not exceptional (e.g. middleware that
    needs to check an ``Authorization`` header).

    Returns
    -------
    dict or None
        The decoded payload, or ``None`` if validation failed.
    """
    try:
        return decode_jwt_token(token, secret_key=secret_key)
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Public API — OAuth Token Storage
# ---------------------------------------------------------------------------


def _token_path(provider: str) -> Path:
    """Return the filesystem path for a provider's encrypted token file."""
    safe_name = "".join(c if c.isalnum() else "_" for c in provider.lower())
    return _TOKEN_STORE_DIR / f"{safe_name}.token"


def store_token(provider: str, token_data: Dict[str, Any]) -> None:
    """Persist an OAuth token for *provider* to encrypted storage.

    The token data dict is JSON-serialised, encrypted with the application
    ``ENCRYPTION_KEY``, and written to disk.

    Parameters
    ----------
    provider:
        OAuth provider name (e.g. ``"google"``, ``"facebook"``).
    token_data:
        The token payload — typically contains ``access_token``,
        ``refresh_token``, ``expires_at``, etc.
    """
    _TOKEN_STORE_DIR.mkdir(parents=True, exist_ok=True)
    plaintext = json.dumps(token_data, default=str)
    encrypted = encrypt_data(plaintext)
    _token_path(provider).write_text(encrypted, encoding="utf-8")


def get_token(provider: str) -> Optional[Dict[str, Any]]:
    """Retrieve a stored OAuth token for *provider*.

    Parameters
    ----------
    provider:
        OAuth provider name.

    Returns
    -------
    dict or None
        The decrypted token data, or ``None`` if no token exists for this
        provider or decryption fails.
    """
    path = _token_path(provider)
    if not path.exists():
        return None
    try:
        encrypted = path.read_text(encoding="utf-8")
        plaintext = decrypt_data(encrypted)
        return json.loads(plaintext)
    except (InvalidToken, json.JSONDecodeError, OSError):
        return None


def delete_token(provider: str) -> bool:
    """Delete the stored OAuth token for *provider*.

    Returns
    -------
    bool
        ``True`` if a token file was deleted, ``False`` if none existed.
    """
    path = _token_path(provider)
    if path.exists():
        path.unlink()
        return True
    return False
