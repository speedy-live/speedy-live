"""Internal engine boundary.

Concrete model implementations will live behind this interface. No third-party
hosted inference API is called here. This placeholder deliberately cannot generate
media until an owned/approved engine implementation is installed.
"""
from abc import ABC, abstractmethod
from pathlib import Path
from typing import AsyncIterator

from app.schemas import GenerationRequest, MotionFrame


class AnimationEngineUnavailable(RuntimeError):
    """Raised when no qualified local SPEEDY LIVE engine is installed."""


class AnimationEngine(ABC):
    name: str
    version: str

    @abstractmethod
    async def generate_recording(
        self,
        request: GenerationRequest,
        source_image: Path,
        driving_video: Path,
        output_path: Path,
    ) -> Path:
        """Generate a recording using locally controlled inference infrastructure."""
        raise NotImplementedError

    @abstractmethod
    async def generate_live_frames(
        self,
        source_image: Path,
        motion: AsyncIterator[MotionFrame],
    ) -> AsyncIterator[bytes]:
        """Yield encoded frames for a future real-time media pipeline."""
        raise NotImplementedError


class UnconfiguredAnimationEngine(AnimationEngine):
    name = "unconfigured"
    version = "0"

    async def generate_recording(
        self,
        request: GenerationRequest,
        source_image: Path,
        driving_video: Path,
        output_path: Path,
    ) -> Path:
        raise AnimationEngineUnavailable(
            "No SPEEDY LIVE animation model has been trained or installed."
        )

    async def generate_live_frames(
        self,
        source_image: Path,
        motion: AsyncIterator[MotionFrame],
    ) -> AsyncIterator[bytes]:
        raise AnimationEngineUnavailable(
            "The real-time SPEEDY LIVE animation engine is not available."
        )
        yield b""  # Makes this an async generator while remaining unreachable.
