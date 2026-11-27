"""Validation for locally owned/approved animation model artifacts.

This module never downloads models or calls hosted inference services. A model is
accepted only when its checkpoint hash and commercial-rights declaration match.
"""
from hashlib import sha256
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, ValidationError


class ModelManifest(BaseModel):
    model_id: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9._-]+$")
    version: str = Field(min_length=1, max_length=40)
    task: Literal["portrait_animation", "full_body_animation"]
    checkpoint_file: str = Field(min_length=1, max_length=255)
    checkpoint_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    architecture: str = Field(min_length=3, max_length=120)
    input_contract: Literal["speedy_motion_v1"]
    output_contract: Literal["rgb_frames_v1"]
    commercial_use_allowed: bool
    training_data_consent_verified: bool


class ModelArtifactError(ValueError):
    """Raised when a local model artifact is missing or not qualified."""


def verify_model_artifact(manifest_path: Path) -> ModelManifest:
    """Validate metadata, explicit rights, consent and checkpoint integrity."""
    try:
        manifest = ModelManifest.model_validate_json(manifest_path.read_text("utf-8"))
    except (OSError, ValidationError) as exc:
        raise ModelArtifactError(f"Invalid or unreadable model manifest: {exc}") from exc

    if not manifest.commercial_use_allowed:
        raise ModelArtifactError("Model is not approved for commercial use.")
    if not manifest.training_data_consent_verified:
        raise ModelArtifactError("Training-data consent has not been verified.")

    checkpoint = (manifest_path.parent / manifest.checkpoint_file).resolve()
    root = manifest_path.parent.resolve()
    if root not in checkpoint.parents:
        raise ModelArtifactError("Checkpoint must be stored beside or below its manifest.")
    if not checkpoint.is_file():
        raise ModelArtifactError("Model checkpoint file is missing.")

    digest = sha256(checkpoint.read_bytes()).hexdigest()
    if digest != manifest.checkpoint_sha256:
        raise ModelArtifactError("Model checkpoint SHA-256 does not match its manifest.")
    return manifest
