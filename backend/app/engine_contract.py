"""Machine-readable engine qualification contract.

This module describes evidence required before a model can be enabled. It does
not download weights, run inference, or establish that a licence claim is true.
"""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

EngineMode = Literal["portrait", "full_body"]


class EngineQualificationError(ValueError):
    """Raised when an engine is not eligible for a requested product mode."""


class EngineManifest(BaseModel):
    """Auditable metadata supplied by a locally operated model adapter."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    engine_id: str = Field(min_length=2, max_length=100)
    version: str = Field(min_length=1, max_length=80)
    supported_modes: tuple[EngineMode, ...] = Field(min_length=1)
    supports_streaming: bool
    supports_audio_driven_portrait: bool = False
    checkpoint_sha256: str | None = None
    code_license: str = Field(min_length=1, max_length=120)
    weights_license: str = Field(min_length=1, max_length=120)
    dependency_review_id: str | None = None
    dataset_rights_review_id: str | None = None
    commercial_rights_verified: bool = False
    inference_entrypoint: str | None = None
    minimum_gpu_memory_gb: float | None = Field(default=None, gt=0)
    tested_gpu: str | None = None

    @field_validator("checkpoint_sha256")
    @classmethod
    def validate_checkpoint_hash(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[a-fA-F0-9]{64}", value):
            raise ValueError("checkpoint_sha256 must be a 64-character SHA-256 hex digest.")
        return value

    @property
    def has_runnable_artifact(self) -> bool:
        return bool(self.checkpoint_sha256 and self.inference_entrypoint)

    @property
    def rights_review_complete(self) -> bool:
        return bool(
            self.commercial_rights_verified
            and self.dependency_review_id
            and self.dataset_rights_review_id
        )

    @property
    def eligible_for_private_test(self) -> bool:
        return self.has_runnable_artifact and self.rights_review_complete


def require_engine_eligibility(
    manifest: EngineManifest,
    mode: EngineMode,
    *,
    require_commercial_rights: bool = True,
) -> None:
    """Fail closed if a model cannot support the requested path."""
    if mode not in manifest.supported_modes:
        raise EngineQualificationError(
            f"Engine {manifest.engine_id} does not support {mode} mode."
        )
    if mode == "portrait" and not manifest.supports_streaming:
        raise EngineQualificationError(
            f"Engine {manifest.engine_id} cannot be used for live portrait streaming."
        )
    if not manifest.has_runnable_artifact:
        raise EngineQualificationError(
            f"Engine {manifest.engine_id} has no verified checkpoint and inference entrypoint."
        )
    if require_commercial_rights and not manifest.rights_review_complete:
        raise EngineQualificationError(
            f"Engine {manifest.engine_id} has not passed the commercial-rights review."
        )
