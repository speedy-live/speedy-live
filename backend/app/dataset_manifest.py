"""Validation for consented, provenance-tracked animation datasets.

This validates declarations; it cannot independently prove that consent or a licence is genuine.
"""
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class DatasetAsset(BaseModel):
    asset_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    subject_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    source_type: Literal["image", "video", "audio"]
    source_reference: str = Field(min_length=8, max_length=500)
    consent_record_id: str = Field(min_length=3, max_length=128)
    permitted_purposes: list[Literal["training", "validation", "testing", "commercial_generation"]] = Field(min_length=1)
    commercial_use_allowed: bool
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    width: int | None = Field(default=None, gt=0, le=16384)
    height: int | None = Field(default=None, gt=0, le=16384)
    fps: float | None = Field(default=None, gt=0, le=240)
    duration_ms: int | None = Field(default=None, gt=0)
    audio_present: bool = False
    face_visible: bool | None = None
    body_visibility: Literal["none", "partial", "full", "unknown"] = "unknown"
    left_hand_visible: bool | None = None
    right_hand_visible: bool | None = None
    occlusion: str = Field(default="unknown", max_length=80)
    camera_view: str = Field(default="unknown", max_length=80)

    @model_validator(mode="after")
    def validate_source_and_media(self):
        ref = self.source_reference.strip()
        if not (ref.startswith("private://") or ref.startswith("dataset://")):
            raise ValueError("source_reference must use a private:// or dataset:// reference.")
        if self.source_type == "image" and (self.width is None or self.height is None):
            raise ValueError("Image assets require width and height.")
        if self.source_type == "video" and (
            self.width is None or self.height is None or self.fps is None or self.duration_ms is None
        ):
            raise ValueError("Video assets require width, height, fps and duration_ms.")
        if self.source_type == "audio" and self.duration_ms is None:
            raise ValueError("Audio assets require duration_ms.")
        if self.commercial_use_allowed and "commercial_generation" not in self.permitted_purposes:
            raise ValueError("Commercially cleared assets must permit commercial_generation.")
        return self


class DatasetManifest(BaseModel):
    dataset_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    version: str = Field(min_length=1, max_length=40)
    purpose: Literal["training", "validation", "testing"]
    commercial_use_allowed: bool
    consent_audit_verified: bool
    assets: list[DatasetAsset] = Field(min_length=1, max_length=1_000_000)

    @model_validator(mode="after")
    def validate_dataset(self):
        ids = [asset.asset_id for asset in self.assets]
        if len(ids) != len(set(ids)):
            raise ValueError("asset_id values must be unique within a dataset.")
        for asset in self.assets:
            if self.purpose not in asset.permitted_purposes:
                raise ValueError(f"Asset {asset.asset_id} does not permit dataset purpose {self.purpose}.")
            if self.commercial_use_allowed and not asset.commercial_use_allowed:
                raise ValueError("A commercially cleared dataset cannot contain an uncleared asset.")
        if self.commercial_use_allowed and not self.consent_audit_verified:
            raise ValueError("Commercial dataset requires a verified consent audit.")
        return self


class DatasetManifestError(ValueError):
    """Raised when a dataset manifest is invalid or not qualified."""


def validate_dataset_manifest_json(raw_json: str) -> DatasetManifest:
    """Parse and validate a dataset manifest; rights declarations still need human audit."""
    try:
        return DatasetManifest.model_validate_json(raw_json)
    except ValidationError as exc:
        raise DatasetManifestError(f"Invalid dataset manifest: {exc}") from exc
