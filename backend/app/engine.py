"""Internal engine boundary and fail-closed engine registry.

Concrete adapters must run on infrastructure operated by SPEEDY LIVE. No hosted
animation API is called by this module. Registration verifies the actual local
checkpoint against a rights-reviewed model manifest. Runtime health is a
separate gate: a verified manifest alone never makes an engine operational.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from app.engine_contract import EngineManifest, EngineQualificationError, require_engine_eligibility
from app.model_manifest import ModelArtifactError, verify_model_artifact
from app.schemas import GenerationRequest, MotionFrame
from app.audio_contract import AudioChunk


class AnimationEngineUnavailable(RuntimeError):
    """Raised when no qualified local SPEEDY LIVE engine is installed."""


class AnimationEngine(ABC):
    name: str
    version: str

    async def health_check(self) -> bool:
        """Return True only after the real model runtime completes a safe self-test.

        Adapters must override this method. The default deliberately fails closed,
        so legacy adapters and test stubs cannot appear production-ready.
        """
        return False

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
    """Holds locally verified engines and separately tracks runtime qualification."""

    def __init__(self) -> None:
        self._engine: AnimationEngine | None = None
        self._manifest: EngineManifest | None = None
        self._runtime_healthy = False
        self._runtime_error: str | None = None

    def register(self, engine: AnimationEngine, manifest: EngineManifest,
                 artifact_manifest_path: Path) -> None:
        self.clear()
        if engine.name != manifest.engine_id or engine.version != manifest.version:
            raise EngineQualificationError("Engine identity/version does not match its qualification manifest.")
        if not manifest.eligible_for_private_test:
            raise EngineQualificationError("Engine has not passed the artifact and commercial-rights review.")
        try:
            artifact = verify_model_artifact(artifact_manifest_path)
        except ModelArtifactError as exc:
            raise EngineQualificationError(f"Local model artifact verification failed: {exc}") from exc

        expected_task = {"portrait": "portrait_animation", "full_body": "full_body_animation"}
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

    async def check_runtime(self) -> bool:
        """Run the adapter's real self-test and remember the result."""
        self._runtime_healthy = False
        self._runtime_error = None
        if self._engine is None or self._manifest is None:
            self._runtime_error = "No qualified local animation engine is registered."
            return False
        try:
            self._runtime_healthy = (await self._engine.health_check()) is True
            if not self._runtime_healthy:
                self._runtime_error = "The engine adapter did not pass its real runtime self-test."
        except Exception as exc:
            self._runtime_error = f"Engine runtime self-test failed: {type(exc).__name__}: {exc}"
        return self._runtime_healthy

    def clear(self) -> None:
        self._engine = None
        self._manifest = None
        self._runtime_healthy = False
        self._runtime_error = None

    @property
    def configured(self) -> bool:
        return self._engine is not None and self._manifest is not None

    @property
    def operational(self) -> bool:
        return self.configured and self._runtime_healthy

    def status(self) -> dict[str, object]:
        if not self.configured:
            return {
                "configured": False, "runtime_healthy": False, "operational": False,
                "engine_id": "unconfigured", "version": None, "supported_modes": [],
                "supports_streaming": False, "commercial_rights_verified": False,
                "runtime_error": self._runtime_error,
                "message": "No qualified local animation engine is registered.",
            }
        assert self._manifest is not None
        return {
            "configured": True, "runtime_healthy": self._runtime_healthy,
            "operational": self.operational, "engine_id": self._manifest.engine_id,
            "version": self._manifest.version,
            "supported_modes": list(self._manifest.supported_modes),
            "supports_streaming": self._manifest.supports_streaming,
            "commercial_rights_verified": self._manifest.rights_review_complete,
            "runtime_error": self._runtime_error,
            "message": (
                "Engine passed its runtime self-test."
                if self.operational else
                "Artifact and rights checks passed; runtime inference qualification has not passed."
            ),
        }

    def get(self, mode: str, *, live: bool = False) -> AnimationEngine:
        if not self.configured or self._engine is None or self._manifest is None:
            raise AnimationEngineUnavailable("No qualified local animation engine is registered.")
        if not self.operational:
            raise AnimationEngineUnavailable("The local animation engine has not passed its runtime health check.")
        require_engine_eligibility(self._manifest, mode, require_commercial_rights=True)
        if live and not self._manifest.supports_streaming:
            raise AnimationEngineUnavailable("The registered engine does not support live streaming.")
        return self._engine
