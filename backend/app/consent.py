"""Explicit consent contracts. These schemas do not persist or authenticate consent."""
from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator, model_validator


class ConsentPurpose(StrEnum):
    PHOTO_ANIMATION = "photo_animation"
    LIVE_CALLING = "live_calling"
    RECORDING = "recording"


class ConsentRecord(BaseModel):
    """A proposed consent record to be stored only by an authenticated consent service."""

    consent_record_id: str = Field(min_length=12, max_length=128)
    owner_user_id: str = Field(min_length=8, max_length=128)
    subject_is_uploader: bool
    rights_to_use_image_confirmed: bool
    subject_permission_confirmed: bool
    purposes: set[ConsentPurpose] = Field(min_length=1, max_length=3)
    policy_version: str = Field(min_length=1, max_length=32)
    recorded_at: datetime

    @field_validator("recorded_at")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Consent timestamp must include a timezone.")
        if value > datetime.now(timezone.utc):
            raise ValueError("Consent timestamp cannot be in the future.")
        return value

    @model_validator(mode="after")
    def require_all_rights_and_permissions(self):
        if not self.rights_to_use_image_confirmed:
            raise ValueError("The uploader must confirm they have rights to use the image.")
        if not self.subject_permission_confirmed:
            raise ValueError("Permission from the person depicted is required.")
        return self


class ConsentRevocation(BaseModel):
    consent_record_id: str = Field(min_length=12, max_length=128)
    owner_user_id: str = Field(min_length=8, max_length=128)
    revoked_at: datetime

    @field_validator("revoked_at")
    @classmethod
    def require_timezone_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Revocation timestamp must include a timezone.")
        if value > datetime.now(timezone.utc):
            raise ValueError("Revocation timestamp cannot be in the future.")
        return value
