from datetime import datetime, timezone

import pytest

from app.consent import ConsentPurpose, ConsentRecord
from app.media_access import MediaAccessDenied
from app.media_repository import SQLiteMediaRepository
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
    with pytest.raises(Exception):
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
    with pytest.raises(Exception):
        service.upload(
            actor_user_id="customer_0001",
            consent_record_id="missing_consent_001",
            image_bytes=image_bytes(),
        )
    assert list(store.root.iterdir()) == []
