"""Internal engine boundary and fail-closed engine registry.

Concrete adapters must run on infrastructure operated by SPEEDY LIVE. No hosted
animation API is called by this module. Registration verifies the actual local
checkpoint against a rights-reviewed model manifest.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from app.engine_contract import EngineManifest, EngineQualificationError, require_engine_eligibility
from app.model_manifest import ModelArtifactError, verify_model_artifact
from app.schemas import GenerationRequest, MotionFrame


class AnimationEngineUnavailable(RuntimeError):
    """Raised when no qualified local SPEEDY LIVE engine is installed."""


class AnimationEngine(ABC):
    name: str
    version: str

    @abstractmethod
    async def generate_recording(self, request: GenerationRequest, source_image: Path,
                                 driving_video: Path, output_path: Path) -> Path:
        raise NotImplementedError

    @abstractmethod
    async def generate_live_frames(self, source_image: Path,
                                   motion: AsyncIterator[MotionFrame]) -> AsyncIterator[bytes]:
        raise NotImplementedError


class UnconfiguredAnimationEngine(AnimationEngine):
    name = "unconfigured"
    version = "0"

    async def generate_recording(self, request, source_image, driving_video, output_path):
        raise AnimationEngineUnavailable("No SPEEDY LIVE animation model has been trained or installed.")

    async def generate_live_frames(self, source_image, motion):
        raise AnimationEngineUnavailable("The real-time SPEEDY LIVE animation engine is not available.")
        yield b""


class EngineRegistry:
    """Holds only locally operated engines with verified local model artifacts."""

    def __init__(self) -> None:
        self._engine: AnimationEngine | None = None
        self._manifest: EngineManifest | None = None

    def register(self, engine: AnimationEngine, manifest: EngineManifest,
                 artifact_manifest_path: Path) -> None:
        if engine.name != manifest.engine_id or engine.version != manifest.version:
            raise EngineQualificationError("Engine identity/version does not match its qualification manifest.")
        if not manifest.eligible_for_private_test:
            raise EngineQualificationError("Engine has not passed the artifact and commercial-rights review.")
        try:
            artifact = verify_model_artifact(artifact_manifest_path)
        except ModelArtifactError as exc:
            raise EngineQualificationError(f"Local model artifact verification failed: {exc}") from exc

        expected_task = {
            "portrait": "portrait_animation",
            "full_body": "full_body_animation",
        }
        artifact_modes = {mode for mode, task in expected_task.items() if task == artifact.task}
        if artifact.model_id != manifest.engine_id or artifact.version != manifest.version:
            raise EngineQualificationError("Local model artifact identity/version does not match engine manifest.")
        if artifact.checkpoint_sha256 != manifest.checkpoint_sha256:
            raise EngineQualificationError("Local model checkpoint hash does not match engine manifest.")
        if not set(manifest.supported_modes).issubset(artifact_modes):
            raise EngineQualificationError("Local model artifact task does not match supported engine modes.")
        if not artifact.commercial_use_allowed or not artifact.training_data_consent_verified:
            raise EngineQualificationError("Local model artifact rights and training-data consent are not verified.")
        self._engine, self._manifest = engine, manifest

    def clear(self) -> None:
        self._engine = None
        self._manifest = None

    @property
    def configured(self) -> bool:
        return self._engine is not None and self._manifest is not None

    def status(self) -> dict[str, object]:
        if not self.configured:
            return {"configured": False, "engine_id": "unconfigured", "version": None,
                    "supported_modes": [], "supports_streaming": False,
                    "commercial_rights_verified": False,
                    "message": "No qualified local animation engine is registered."}
        assert self._manifest is not None
        return {"configured": True, "engine_id": self._manifest.engine_id,
                "version": self._manifest.version,
                "supported_modes": list(self._manifest.supported_modes),
                "supports_streaming": self._manifest.supports_streaming,
                "commercial_rights_verified": self._manifest.rights_review_complete,
                "message": "Engine registered; runtime inference qualification is still required."}

    def get(self, mode: str, *, live: bool = False) -> AnimationEngine:
        if not self.configured or self._engine is None or self._manifest is None:
            raise AnimationEngineUnavailable("No qualified local animation engine is registered.")
        require_engine_eligibility(self._manifest, mode, require_commercial_rights=True)
        if live and not self._manifest.supports_streaming:
            raise AnimationEngineUnavailable("The registered engine does not support live streaming.")
        return self._engine
