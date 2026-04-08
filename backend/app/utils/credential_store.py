"""
Omura Life Manager — Encrypted Credential Vault
=================================================
Provides AES-256 encrypted storage and retrieval of sensitive credentials
(API keys, OAuth secrets, tokens, etc.) backed by the ``Credential`` database
model and the ``cryptography`` library's Fernet implementation.

The encryption key is derived from the application-wide ``ENCRYPTION_KEY``
setting using SHA-256 + base64url encoding so that an arbitrary-length
passphrase yields a valid 32-byte Fernet key.

Usage::

    from backend.app.utils.credential_store import (
        encrypt_value, decrypt_value,
        store_credential, get_credential,
        list_credentials, delete_credential,
        get_service_credentials,
    )
"""

from __future__ import annotations

import base64
import hashlib
import logging
from typing import Dict, List, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database.models import Credential

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fernet cipher — derived from the configured encryption key
# ---------------------------------------------------------------------------


def _derive_fernet_key(raw_key: str) -> bytes:
    """Derive a URL-safe base64-encoded 32-byte key suitable for Fernet.

    Fernet requires exactly 32 bytes, base64url-encoded (44 characters with
    padding).  We hash the arbitrary-length passphrase with SHA-256 to
    normalise it to 32 bytes, then base64url-encode the result.

    Parameters
    ----------
    raw_key:
        Arbitrary-length passphrase string.

    Returns
    -------
    bytes
        A 44-byte base64url-encoded key ready for ``Fernet()``.
    """
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()  # 32 bytes
    return base64.urlsafe_b64encode(digest)  # 44 bytes b64


_fernet = Fernet(_derive_fernet_key(settings.ENCRYPTION_KEY))

# ---------------------------------------------------------------------------
# Low-level encrypt / decrypt
# ---------------------------------------------------------------------------


def encrypt_value(plaintext: str) -> bytes:
    """Encrypt a plaintext string and return raw ciphertext bytes.

    Parameters
    ----------
    plaintext:
        The string to encrypt.  Must not be empty.

    Returns
    -------
    bytes
        Fernet-encrypted ciphertext (URL-safe base64 encoded internally).

    Raises
    ------
    ValueError
        If *plaintext* is empty or ``None``.
    """
    if not plaintext:
        raise ValueError("plaintext must not be empty")
    return _fernet.encrypt(plaintext.encode("utf-8"))


def decrypt_value(encrypted: bytes) -> str:
    """Decrypt Fernet ciphertext bytes back to a plaintext string.

    Parameters
    ----------
    encrypted:
        The ciphertext bytes produced by :func:`encrypt_value`.

    Returns
    -------
    str
        The original plaintext.

    Raises
    ------
    ValueError
        If *encrypted* is empty or ``None``.
    cryptography.fernet.InvalidToken
        If the ciphertext is invalid, tampered with, or encrypted with a
        different key.
    """
    if not encrypted:
        raise ValueError("encrypted value must not be empty")
    return _fernet.decrypt(encrypted).decode("utf-8")


# ---------------------------------------------------------------------------
# Database-backed credential CRUD
# ---------------------------------------------------------------------------


def store_credential(
    db: Session,
    name: str,
    service: str,
    credential_type: str,
    value: str,
    description: Optional[str] = None,
) -> Credential:
    """Encrypt *value* and persist it as a :class:`Credential` row.

    If a credential with the same *name* already exists it is updated
    in-place (upsert behaviour) so callers can safely rotate secrets.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    name:
        Unique human-readable identifier, e.g. ``"google_client_secret"``.
    service:
        Logical service group, e.g. ``"google"``, ``"stripe"``.
    credential_type:
        Kind of secret — ``"api_key"``, ``"oauth_token"``, etc.
    value:
        The plaintext secret to store.  Encrypted before touching the DB.
    description:
        Optional free-text note about this credential.

    Returns
    -------
    Credential
        The created or updated ORM instance (already committed).
    """
    encrypted = encrypt_value(value)

    existing: Optional[Credential] = (
        db.query(Credential).filter(Credential.name == name).first()
    )

    if existing is not None:
        existing.service = service
        existing.credential_type = credential_type
        existing.encrypted_value = encrypted
        existing.description = description
        db.commit()
        db.refresh(existing)
        logger.info("Updated credential '%s' for service '%s'.", name, service)
        return existing

    credential = Credential(
        name=name,
        service=service,
        credential_type=credential_type,
        encrypted_value=encrypted,
        description=description,
    )
    db.add(credential)
    db.commit()
    db.refresh(credential)
    logger.info("Stored new credential '%s' for service '%s'.", name, service)
    return credential


def get_credential(db: Session, name: str) -> Optional[str]:
    """Retrieve and decrypt a single credential by *name*.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    name:
        The unique credential name.

    Returns
    -------
    str or None
        The decrypted plaintext value, or ``None`` if the credential does
        not exist or decryption fails.
    """
    row: Optional[Credential] = (
        db.query(Credential).filter(Credential.name == name).first()
    )
    if row is None:
        return None

    try:
        return decrypt_value(row.encrypted_value)
    except (InvalidToken, ValueError) as exc:
        logger.error(
            "Failed to decrypt credential '%s': %s", name, exc,
        )
        return None


def list_credentials(db: Session) -> List[Dict[str, object]]:
    """Return metadata for every stored credential — *without* decrypted values.

    This is safe to expose to front-end or audit endpoints because the
    actual secret material is never included.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.

    Returns
    -------
    list[dict]
        Each dict contains ``id``, ``name``, ``service``, ``type``,
        ``description``, ``created_at``, and ``updated_at``.
    """
    rows = db.query(Credential).order_by(Credential.service, Credential.name).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "service": row.service,
            "type": row.credential_type,
            "description": row.description,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


def delete_credential(db: Session, name: str) -> bool:
    """Remove a credential by *name*.

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    name:
        The unique credential name to delete.

    Returns
    -------
    bool
        ``True`` if a credential was found and deleted, ``False`` otherwise.
    """
    row: Optional[Credential] = (
        db.query(Credential).filter(Credential.name == name).first()
    )
    if row is None:
        return False

    db.delete(row)
    db.commit()
    logger.info("Deleted credential '%s'.", name)
    return True


def get_service_credentials(db: Session, service: str) -> Dict[str, str]:
    """Return all decrypted credentials belonging to *service* as a dict.

    This is the primary helper for agent code that needs several related
    secrets at once (e.g. ``client_id`` + ``client_secret`` for an OAuth
    flow).

    Parameters
    ----------
    db:
        Active SQLAlchemy session.
    service:
        The service identifier (e.g. ``"google"``).

    Returns
    -------
    dict[str, str]
        Mapping of ``credential.name`` to the decrypted plaintext value.
        Credentials that fail to decrypt are silently omitted and an error
        is logged.
    """
    rows = db.query(Credential).filter(Credential.service == service).all()
    result: Dict[str, str] = {}

    for row in rows:
        try:
            result[row.name] = decrypt_value(row.encrypted_value)
        except (InvalidToken, ValueError) as exc:
            logger.error(
                "Failed to decrypt credential '%s' (service=%s): %s",
                row.name,
                service,
                exc,
            )

    return result
