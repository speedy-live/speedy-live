from datetime import datetime, timezone

import pytest

from app.consent import ConsentPurpose, ConsentRecord, ConsentRevocation
from app.media_access import MediaAccessDenied
from app.media_repository import MediaRepositoryError, SQLiteMediaRepository


def make_consent(owner="customer_0001", consent_id="consent_record_001", purposes=None):
    return ConsentRecord(
        consent_record_id=consent_id,
        owner_user_id=owner,
        subject_is_uploader=False,
        rights_to_use_image_confirmed=True,
        subject_permission_confirmed=True,
        purposes=purposes or [ConsentPurpose.PHOTO_ANIMATION, ConsentPurpose.RECORDING],
        policy_version="2026-01",
        recorded_at=datetime.now(timezone.utc),
    )


def setup_repo(tmp_path):
    repo = SQLiteMediaRepository(tmp_path / "private" / "media.sqlite3")
    record = make_consent()
    repo.save_consent(record)
    return repo, record


def register(repo, record, media_id="a" * 32):
    return repo.register_media(
        media_id=media_id,
        owner_user_id=record.owner_user_id,
        consent_record_id=record.consent_record_id,
        image_format="JPEG",
        content_type="image/jpeg",
        width=320,
        height=240,
        byte_count=2048,
    )


def test_persists_consent_and_media_metadata_and_reloads_after_reopen(tmp_path):
    repo, consent = setup_repo(tmp_path)
    register(repo, consent)
    reopened = SQLiteMediaRepository(tmp_path / "private" / "media.sqlite3")
    media = reopened.get_authorized_media(
        media_id="a" * 32,
        actor_user_id="customer_0001",
        purpose=ConsentPurpose.PHOTO_ANIMATION,
    )
    assert media.owner_user_id == "customer_0001"
    assert media.consent_record_id == consent.consent_record_id
    assert media.content_type == "image/jpeg"


def test_rejects_media_registration_without_matching_owner_consent(tmp_path):
    repo, _ = setup_repo(tmp_path)
    with pytest.raises(MediaRepositoryError, match="Matching owner consent"):
        repo.register_media(
            media_id="b" * 32, owner_user_id="customer_0002",
            consent_record_id="consent_record_001", image_format="JPEG",
            content_type="image/jpeg", width=320, height=240, byte_count=2048,
        )


def test_rejects_duplicate_consent_and_media_ids(tmp_path):
    repo, record = setup_repo(tmp_path)
    with pytest.raises(MediaRepositoryError, match="already exists"):
        repo.save_consent(record)
    register(repo, record)
    with pytest.raises(MediaRepositoryError, match="already exists"):
        register(repo, record)


def test_owner_only_access_and_purpose_scope_are_enforced(tmp_path):
    repo, record = setup_repo(tmp_path)
    register(repo, record)
    with pytest.raises(MediaAccessDenied):
        repo.get_authorized_media(
            media_id="a" * 32, actor_user_id="customer_0002",
            purpose=ConsentPurpose.PHOTO_ANIMATION,
        )
    with pytest.raises(MediaAccessDenied, match="does not cover"):
        repo.get_authorized_media(
            media_id="a" * 32, actor_user_id="customer_0001",
            purpose=ConsentPurpose.LIVE_CALLING,
        )


def test_revocation_is_persistent_and_blocks_future_access_and_registration(tmp_path):
    repo, record = setup_repo(tmp_path)
    register(repo, record)
    repo.revoke_consent(ConsentRevocation(
        consent_record_id=record.consent_record_id,
        owner_user_id=record.owner_user_id,
        revoked_at=datetime.now(timezone.utc),
    ))
    with pytest.raises(MediaAccessDenied, match="revoked"):
        repo.get_authorized_media(
            media_id="a" * 32, actor_user_id="customer_0001",
            purpose=ConsentPurpose.PHOTO_ANIMATION,
        )
    with pytest.raises(MediaRepositoryError, match="Revoked consent"):
        register(repo, record, media_id="b" * 32)


def test_revocation_rejects_another_users_consent_id(tmp_path):
    repo, _ = setup_repo(tmp_path)
    with pytest.raises(MediaRepositoryError, match="not found for this owner"):
        repo.revoke_consent(ConsentRevocation(
            consent_record_id="consent_record_001", owner_user_id="customer_0002",
            revoked_at=datetime.now(timezone.utc),
        ))


def test_delete_metadata_is_owner_only_and_removes_record(tmp_path):
    repo, record = setup_repo(tmp_path)
    register(repo, record)
    with pytest.raises(MediaAccessDenied):
        repo.delete_media_record(media_id="a" * 32, actor_user_id="customer_0002")
    removed = repo.delete_media_record(media_id="a" * 32, actor_user_id="customer_0001")
    assert removed.media_id == "a" * 32
    with pytest.raises(MediaRepositoryError, match="not found"):
        repo.get_authorized_media(
            media_id="a" * 32, actor_user_id="customer_0001",
            purpose=ConsentPurpose.PHOTO_ANIMATION,
        )


def test_database_directory_and_file_permissions_are_private(tmp_path):
    repo, _ = setup_repo(tmp_path)
    assert repo.database_path.parent.stat().st_mode & 0o777 == 0o700
    assert repo.database_path.stat().st_mode & 0o777 == 0o600
