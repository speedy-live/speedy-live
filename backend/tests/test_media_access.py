from datetime import datetime, timezone

import pytest

from app.consent import ConsentPurpose, ConsentRecord, ConsentRevocation
from app.media_access import MediaAccessDenied, authorize_media_use


def consent(**overrides):
    data = {
        "consent_record_id": "consent_record_001",
        "owner_user_id": "customer_0001",
        "subject_is_uploader": False,
        "rights_to_use_image_confirmed": True,
        "subject_permission_confirmed": True,
        "purposes": [ConsentPurpose.PHOTO_ANIMATION, ConsentPurpose.RECORDING],
        "policy_version": "2026-01",
        "recorded_at": datetime.now(timezone.utc),
    }
    data.update(overrides)
    return ConsentRecord(**data)


def authorize(record=None, **overrides):
    args = {
        "actor_user_id": "customer_0001",
        "media_owner_user_id": "customer_0001",
        "media_consent_record_id": "consent_record_001",
        "consent": record or consent(),
        "purpose": ConsentPurpose.PHOTO_ANIMATION,
    }
    args.update(overrides)
    return authorize_media_use(**args)


def test_owner_with_matching_purpose_and_consent_is_authorized():
    authorize()


@pytest.mark.parametrize(
    "overrides",
    [
        {"actor_user_id": "customer_0002"},
        {"media_owner_user_id": "customer_0002"},
        {"media_consent_record_id": "consent_record_other"},
    ],
)
def test_cross_account_or_mismatched_consent_is_denied(overrides):
    with pytest.raises(MediaAccessDenied):
        authorize(**overrides)


def test_consent_must_cover_the_exact_requested_purpose():
    with pytest.raises(MediaAccessDenied, match="does not cover"):
        authorize(purpose=ConsentPurpose.LIVE_CALLING)


def test_revoked_consent_blocks_processing():
    record = consent()
    revoked = ConsentRevocation(
        consent_record_id=record.consent_record_id,
        owner_user_id=record.owner_user_id,
        revoked_at=datetime.now(timezone.utc),
    )
    with pytest.raises(MediaAccessDenied, match="revoked"):
        authorize(record=record, revocation=revoked)


def test_revocation_for_another_account_does_not_revoke_this_record():
    record = consent()
    unrelated = ConsentRevocation(
        consent_record_id=record.consent_record_id,
        owner_user_id="customer_0002",
        revoked_at=datetime.now(timezone.utc),
    )
    authorize(record=record, revocation=unrelated)
