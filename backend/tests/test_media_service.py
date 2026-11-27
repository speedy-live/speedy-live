from datetime import datetime, timezone

import pytest

from app.consent import ConsentPurpose, ConsentRecord
from app.media_access import MediaAccessDenied
from app.media_repository import MediaRepositoryError, SQLiteMediaRepository
from app.media_service import MediaServiceError, PrivateMediaService
from app.media_storage import PrivateLocalMediaStore
from PIL import Image
from io import BytesIO


def image_bytes():
    output = BytesIO()
    Image.new("RGB", (160, 120), (40, 90, 130)).save(output, format="JPEG")
    return output.getvalue()


def setup_service(tmp_path):
    store = PrivateLocalMediaStore(tmp_path / "media")
    repository = SQLiteMediaRepository(tmp_path / "metadata" / "media.sqlite3")
    consent = ConsentRecord(
        consent_record_id="consent_record_001",
        owner_user_id="customer_0001",
        subject_is_uploader=False,
        rights_to_use_image_confirmed=True,
        subject_permission_confirmed=True,
        purposes=[ConsentPurpose.PHOTO_ANIMATION, ConsentPurpose.RECORDING],
        policy_version="2026-01",
        recorded_at=datetime.now(timezone.utc),
    )
    repository.save_consent(consent)
    return PrivateMediaService(storage=store, repository=repository), store, repository


def test_upload_registers_metadata_and_retrieve_checks_owner_and_consent(tmp_path):
    service, store, _ = setup_service(tmp_path)
    stored = service.upload(
        actor_user_id="customer_0001",
        consent_record_id="consent_record_001",
        image_bytes=image_bytes(),
    )
    record, payload = service.retrieve(
        media_id=stored.media_id,
        actor_user_id="customer_0001",
        purpose=ConsentPurpose.PHOTO_ANIMATION,
    )
    assert record.media_id == stored.media_id
    assert payload == image_bytes()
    with pytest.raises(MediaAccessDenied):
        service.retrieve(
            media_id=stored.media_id,
            actor_user_id="customer_0002",
            purpose=ConsentPurpose.PHOTO_ANIMATION,
        )


def test_failed_metadata_registration_compensates_by_deleting_image(tmp_path):
    service, store, _ = setup_service(tmp_path)
    with pytest.raises(MediaRepositoryError, match="Matching owner consent"):
        service.upload(
            actor_user_id="customer_0002",
            consent_record_id="consent_record_001",
            image_bytes=image_bytes(),
        )
    assert list(store.root.iterdir()) == []


def test_upload_requires_authenticated_actor_identifier(tmp_path):
    service, store, _ = setup_service(tmp_path)
    with pytest.raises(MediaAccessDenied):
        service.upload(
            actor_user_id="",
            consent_record_id="consent_record_001",
            image_bytes=image_bytes(),
        )
    assert list(store.root.iterdir()) == []


def test_upload_with_revoked_or_missing_consent_does_not_leave_file(tmp_path):
    service, store, _ = setup_service(tmp_path)
    with pytest.raises(MediaRepositoryError, match="Matching owner consent"):
        service.upload(
            actor_user_id="customer_0001",
            consent_record_id="missing_consent_001",
            image_bytes=image_bytes(),
        )
    assert list(store.root.iterdir()) == []


def test_delete_removes_file_and_metadata_for_owner(tmp_path):
    service, store, repository = setup_service(tmp_path)
    stored = service.upload(
        actor_user_id="customer_0001",
        consent_record_id="consent_record_001",
        image_bytes=image_bytes(),
    )
    service.delete(media_id=stored.media_id, actor_user_id="customer_0001")
    assert list(store.root.iterdir()) == []
    assert repository.list_pending_media_deletions() == []


def test_delete_rejects_another_customer(tmp_path):
    service, store, _ = setup_service(tmp_path)
    stored = service.upload(
        actor_user_id="customer_0001",
        consent_record_id="consent_record_001",
        image_bytes=image_bytes(),
    )
    with pytest.raises(MediaAccessDenied):
        service.delete(media_id=stored.media_id, actor_user_id="customer_0002")
    assert len(list(store.root.iterdir())) == 1


def test_delete_failure_keeps_media_hidden_and_retryable(tmp_path, monkeypatch):
    service, store, repository = setup_service(tmp_path)
    stored = service.upload(
        actor_user_id="customer_0001",
        consent_record_id="consent_record_001",
        image_bytes=image_bytes(),
    )
    original_delete = store.delete_image
    def fail_delete(media_id):
        raise MediaStorageError("simulated disk failure")
    monkeypatch.setattr(store, "delete_image", fail_delete)
    with pytest.raises(MediaServiceError, match="retry is required"):
        service.delete(media_id=stored.media_id, actor_user_id="customer_0001")
    assert len(repository.list_pending_media_deletions()) == 1
    with pytest.raises(MediaRepositoryError, match="not found"):
        service.retrieve(
            media_id=stored.media_id,
            actor_user_id="customer_0001",
            purpose=ConsentPurpose.PHOTO_ANIMATION,
        )
    monkeypatch.setattr(store, "delete_image", original_delete)
    service.delete(media_id=stored.media_id, actor_user_id="customer_0001")
    assert list(store.root.iterdir()) == []
    assert repository.list_pending_media_deletions() == []


def test_delete_retries_metadata_finalization_after_file_was_removed(tmp_path, monkeypatch):
    service, store, repository = setup_service(tmp_path)
    stored = service.upload(
        actor_user_id="customer_0001",
        consent_record_id="consent_record_001",
        image_bytes=image_bytes(),
    )
    original_finalize = repository.finalize_media_deletion
    def fail_finalize(media_id):
        raise MediaRepositoryError("simulated database failure")
    monkeypatch.setattr(repository, "finalize_media_deletion", fail_finalize)
    with pytest.raises(MediaServiceError, match="metadata cleanup is pending"):
        service.delete(media_id=stored.media_id, actor_user_id="customer_0001")
    assert list(store.root.iterdir()) == []
    assert len(repository.list_pending_media_deletions()) == 1
    monkeypatch.setattr(repository, "finalize_media_deletion", original_finalize)
    service.delete(media_id=stored.media_id, actor_user_id="customer_0001")
    assert repository.list_pending_media_deletions() == []
