"""Orchestrate private media bytes with persistent ownership/consent metadata.

This is an internal service class. It does not expose routes or authenticate callers;
actor_user_id must come from verified server-side authentication middleware.
"""
from __future__ import annotations

from app.consent import ConsentPurpose
from app.media_access import MediaAccessDenied
from app.media_repository import (
    MediaRecord,
    MediaRepositoryError,
    SQLiteMediaRepository,
)
from app.media_storage import MediaStorageError, PrivateLocalMediaStore, StoredMedia


class MediaServiceError(RuntimeError):
    """Raised when a media operation cannot complete safely."""


class PrivateMediaService:
    def __init__(
        self,
        *,
        storage: PrivateLocalMediaStore,
        repository: SQLiteMediaRepository,
    ):
        self.storage = storage
        self.repository = repository

    def upload(
        self,
        *,
        actor_user_id: str,
        consent_record_id: str,
        image_bytes: bytes,
    ) -> StoredMedia:
        """Store image and register owner metadata; compensate if metadata fails."""
        if not actor_user_id:
            raise MediaAccessDenied("A verified signed-in user is required.")
        stored = self.storage.put_image(image_bytes)
        try:
            self.repository.register_media(
                media_id=stored.media_id,
                owner_user_id=actor_user_id,
                consent_record_id=consent_record_id,
                image_format=stored.format,
                content_type=stored.content_type,
                width=stored.width,
                height=stored.height,
                byte_count=stored.byte_count,
            )
        except Exception as exc:
            try:
                self.storage.delete_image(stored.media_id)
            except MediaStorageError as cleanup_error:
                raise MediaServiceError(
                    "Media registration failed and temporary image cleanup also failed; "
                    "operator reconciliation is required."
                ) from cleanup_error
            if isinstance(exc, (MediaRepositoryError, MediaAccessDenied)):
                raise
            raise MediaServiceError("Could not register uploaded media.") from exc
        return stored

    def retrieve(
        self, *, media_id: str, actor_user_id: str, purpose: ConsentPurpose
    ) -> tuple[MediaRecord, bytes]:
        """Authorize against persisted metadata before reading private image bytes."""
        record = self.repository.get_authorized_media(
            media_id=media_id, actor_user_id=actor_user_id, purpose=purpose
        )
        try:
            data = self.storage.read_image(media_id)
        except MediaStorageError as exc:
            raise MediaServiceError("Authorized media metadata exists but its file is unavailable.") from exc
        return record, data

    def delete(self, *, media_id: str, actor_user_id: str) -> None:
        """Hide media, delete bytes, then finalize metadata; failures remain retryable."""
        record = self.repository.begin_media_deletion(
            media_id=media_id, actor_user_id=actor_user_id
        )
        try:
            self.storage.delete_image(record.media_id)
        except MediaStorageError as exc:
            raise MediaServiceError(
                "Media is hidden but physical deletion failed; retry is required."
            ) from exc
        try:
            self.repository.finalize_media_deletion(media_id=record.media_id)
        except MediaRepositoryError as exc:
            raise MediaServiceError(
                "Media file is deleted but metadata cleanup is pending; retry is required."
            ) from exc
