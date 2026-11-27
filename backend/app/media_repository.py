"""SQLite-backed private media and consent metadata repository.

This repository is an internal persistence layer, not an HTTP API or authentication
system. Callers must derive actor_user_id from a verified server-side session and
must never accept owner IDs or consent records as trusted client assertions.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from collections.abc import Iterator

from app.consent import ConsentPurpose, ConsentRecord, ConsentRevocation
from app.media_access import MediaAccessDenied, authorize_media_use


@dataclass(frozen=True)
class MediaRecord:
    media_id: str
    owner_user_id: str
    consent_record_id: str
    format: str
    content_type: str
    width: int
    height: int
    byte_count: int
    created_at: datetime


class MediaRepositoryError(RuntimeError):
    """Raised when media metadata cannot be safely persisted or retrieved."""


class SQLiteMediaRepository:
    """Persist consent, revocation and media ownership metadata in a private SQLite DB."""

    def __init__(self, database_path: Path):
        self.database_path = Path(database_path)
        if str(self.database_path) == ":memory:":
            raise MediaRepositoryError("Use a file-backed database for persistent metadata.")
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        try:
            self.database_path.parent.chmod(0o700)
            with self._connect() as connection:
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS consent_records (
                        consent_record_id TEXT PRIMARY KEY,
                        owner_user_id TEXT NOT NULL,
                        record_json TEXT NOT NULL,
                        recorded_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS consent_revocations (
                        consent_record_id TEXT PRIMARY KEY
                            REFERENCES consent_records(consent_record_id) ON DELETE RESTRICT,
                        owner_user_id TEXT NOT NULL,
                        revoked_at TEXT NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS media_records (
                        media_id TEXT PRIMARY KEY,
                        owner_user_id TEXT NOT NULL,
                        consent_record_id TEXT NOT NULL
                            REFERENCES consent_records(consent_record_id) ON DELETE RESTRICT,
                        format TEXT NOT NULL,
                        content_type TEXT NOT NULL,
                        width INTEGER NOT NULL CHECK(width > 0),
                        height INTEGER NOT NULL CHECK(height > 0),
                        byte_count INTEGER NOT NULL CHECK(byte_count > 0),
                        created_at TEXT NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS idx_media_owner
                        ON media_records(owner_user_id, created_at);
                    """
                )
            if self.database_path.exists():
                self.database_path.chmod(0o600)
        except (OSError, sqlite3.Error) as exc:
            raise MediaRepositoryError("Could not initialize private media metadata database.") from exc

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        """Open a transaction and always close its underlying SQLite connection."""
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA busy_timeout = 10000")
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    def save_consent(self, consent: ConsentRecord) -> None:
        """Persist a validated consent record; duplicate IDs cannot overwrite history."""
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO consent_records
                    (consent_record_id, owner_user_id, record_json, recorded_at)
                    VALUES (?, ?, ?, ?)""",
                    (
                        consent.consent_record_id,
                        consent.owner_user_id,
                        consent.model_dump_json(),
                        consent.recorded_at.astimezone(timezone.utc).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise MediaRepositoryError("Consent record already exists or is invalid.") from exc
        except sqlite3.Error as exc:
            raise MediaRepositoryError("Could not save consent record.") from exc

    def revoke_consent(self, revocation: ConsentRevocation) -> None:
        """Persist a revocation only for the owner of the existing consent record."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT owner_user_id FROM consent_records WHERE consent_record_id = ?",
                    (revocation.consent_record_id,),
                ).fetchone()
                if row is None or row["owner_user_id"] != revocation.owner_user_id:
                    raise MediaRepositoryError("Consent record was not found for this owner.")
                connection.execute(
                    """INSERT INTO consent_revocations
                    (consent_record_id, owner_user_id, revoked_at) VALUES (?, ?, ?)""",
                    (
                        revocation.consent_record_id,
                        revocation.owner_user_id,
                        revocation.revoked_at.astimezone(timezone.utc).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise MediaRepositoryError("Consent has already been revoked.") from exc
        except sqlite3.Error as exc:
            raise MediaRepositoryError("Could not revoke consent.") from exc

    def register_media(
        self,
        *,
        media_id: str,
        owner_user_id: str,
        consent_record_id: str,
        image_format: str,
        content_type: str,
        width: int,
        height: int,
        byte_count: int,
    ) -> MediaRecord:
        """Register a stored image only when its owner has a matching, active consent."""
        if not owner_user_id:
            raise MediaRepositoryError("A verified owner ID is required.")
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """SELECT c.record_json, r.revoked_at, c.owner_user_id
                    FROM consent_records c
                    LEFT JOIN consent_revocations r
                      ON r.consent_record_id = c.consent_record_id
                    WHERE c.consent_record_id = ?""",
                    (consent_record_id,),
                ).fetchone()
                if row is None or row["owner_user_id"] != owner_user_id:
                    raise MediaRepositoryError("Matching owner consent was not found.")
                if row["revoked_at"] is not None:
                    raise MediaRepositoryError("Revoked consent cannot register new media.")
                consent = ConsentRecord.model_validate_json(row["record_json"])
                if consent.owner_user_id != owner_user_id:
                    raise MediaRepositoryError("Consent owner mismatch.")
                now = self._utc_now()
                connection.execute(
                    """INSERT INTO media_records
                    (media_id, owner_user_id, consent_record_id, format, content_type,
                     width, height, byte_count, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        media_id, owner_user_id, consent_record_id, image_format,
                        content_type, width, height, byte_count, now.isoformat(),
                    ),
                )
                return MediaRecord(
                    media_id=media_id, owner_user_id=owner_user_id,
                    consent_record_id=consent_record_id, format=image_format,
                    content_type=content_type, width=width, height=height,
                    byte_count=byte_count, created_at=now,
                )
        except MediaRepositoryError:
            raise
        except sqlite3.IntegrityError as exc:
            raise MediaRepositoryError("Media record already exists or violates metadata rules.") from exc
        except sqlite3.Error as exc:
            raise MediaRepositoryError("Could not register media metadata.") from exc

    def get_authorized_media(
        self, *, media_id: str, actor_user_id: str, purpose: ConsentPurpose
    ) -> MediaRecord:
        """Load metadata and enforce owner, exact purpose, and current revocation state."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """SELECT m.*, c.record_json, r.revoked_at, r.owner_user_id AS revoked_owner
                    FROM media_records m
                    JOIN consent_records c ON c.consent_record_id = m.consent_record_id
                    LEFT JOIN consent_revocations r
                      ON r.consent_record_id = m.consent_record_id
                    WHERE m.media_id = ?""",
                    (media_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise MediaRepositoryError("Could not retrieve media metadata.") from exc
        if row is None:
            raise MediaRepositoryError("Media record was not found.")
        consent = ConsentRecord.model_validate_json(row["record_json"])
        revocation = None
        if row["revoked_at"] is not None:
            revocation = ConsentRevocation(
                consent_record_id=row["consent_record_id"],
                owner_user_id=row["revoked_owner"],
                revoked_at=datetime.fromisoformat(row["revoked_at"]),
            )
        authorize_media_use(
            actor_user_id=actor_user_id,
            media_owner_user_id=row["owner_user_id"],
            media_consent_record_id=row["consent_record_id"],
            consent=consent,
            purpose=purpose,
            revocation=revocation,
        )
        return MediaRecord(
            media_id=row["media_id"], owner_user_id=row["owner_user_id"],
            consent_record_id=row["consent_record_id"], format=row["format"],
            content_type=row["content_type"], width=row["width"],
            height=row["height"], byte_count=row["byte_count"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )

    def delete_media_record(self, *, media_id: str, actor_user_id: str) -> MediaRecord:
        """Delete metadata for its owner; caller must delete the private file as well."""
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT * FROM media_records WHERE media_id = ?", (media_id,)
                ).fetchone()
                if row is None:
                    raise MediaRepositoryError("Media record was not found.")
                if not actor_user_id or row["owner_user_id"] != actor_user_id:
                    raise MediaAccessDenied("The signed-in user does not own this media asset.")
                connection.execute("DELETE FROM media_records WHERE media_id = ?", (media_id,))
                return MediaRecord(
                    media_id=row["media_id"], owner_user_id=row["owner_user_id"],
                    consent_record_id=row["consent_record_id"], format=row["format"],
                    content_type=row["content_type"], width=row["width"],
                    height=row["height"], byte_count=row["byte_count"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                )
        except (MediaRepositoryError, MediaAccessDenied):
            raise
        except sqlite3.Error as exc:
            raise MediaRepositoryError("Could not delete media metadata.") from exc
