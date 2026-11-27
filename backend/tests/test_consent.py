from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.consent import ConsentPurpose, ConsentRecord, ConsentRevocation


def valid_record(**overrides):
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
    return data


def test_valid_consent_record_accepts_multiple_explicit_purposes():
    record = ConsentRecord(**valid_record())
    assert ConsentPurpose.PHOTO_ANIMATION in record.purposes
    assert ConsentPurpose.RECORDING in record.purposes


@pytest.mark.parametrize(
    "overrides",
    [
        {"rights_to_use_image_confirmed": False},
        {"subject_permission_confirmed": False},
        {"purposes": []},
        {"recorded_at": datetime.now()},
        {"recorded_at": datetime.now(timezone.utc).replace(year=2099)},
    ],
)
def test_consent_rejects_missing_rights_or_invalid_metadata(overrides):
    with pytest.raises(ValidationError):
        ConsentRecord(**valid_record(**overrides))


def test_revocation_requires_timezone_aware_timestamp():
    revocation = ConsentRevocation(
        consent_record_id="consent_record_001",
        owner_user_id="customer_0001",
        revoked_at=datetime.now(timezone.utc),
    )
    assert revocation.consent_record_id == "consent_record_001"

    with pytest.raises(ValidationError):
        ConsentRevocation(
            consent_record_id="consent_record_001",
            owner_user_id="customer_0001",
            revoked_at=datetime.now(),
        )
