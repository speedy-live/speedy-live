"""Stable internal contracts shared by capture, research and inference layers."""
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


class GenerationMode(StrEnum):
    RECORDING = "recording"
    LIVE = "live"


class JobState(StrEnum):
    QUEUED = "queued"
    PREPROCESSING = "preprocessing"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Landmark(BaseModel):
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    z: float = Field(default=0.0, ge=-10.0, le=10.0)
    visibility: float | None = Field(default=None, ge=0.0, le=1.0)


class HandLandmarks(BaseModel):
    handedness: str = Field(min_length=1, max_length=32)
    landmarks: list[Landmark] = Field(default_factory=list, max_length=30)


class FaceControls(BaseModel):
    yaw_degrees: float = Field(default=0.0, ge=-90.0, le=90.0)
    pitch_degrees: float = Field(default=0.0, ge=-90.0, le=90.0)
    roll_degrees: float = Field(default=0.0, ge=-90.0, le=90.0)
    blendshapes: dict[str, float] = Field(default_factory=dict)

    @field_validator("blendshapes")
    @classmethod
    def validate_blendshape_scores(cls, values: dict[str, float]) -> dict[str, float]:
        if any(not 0.0 <= score <= 1.0 for score in values.values()):
            raise ValueError("Blendshape scores must be between 0 and 1.")
        return values


class MotionFrame(BaseModel):
    sequence: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    body_landmarks: list[Landmark] = Field(default_factory=list, max_length=100)
    hands: list[HandLandmarks] = Field(default_factory=list, max_length=2)
    face: FaceControls = Field(default_factory=FaceControls)


class GenerationRequest(BaseModel):
    mode: GenerationMode
    source_media_id: str = Field(min_length=8, max_length=128)
    motion_media_id: str | None = Field(default=None, min_length=8, max_length=128)
    consent_record_id: str = Field(min_length=8, max_length=128)
    output_format: Literal["mp4", "webm"] = "mp4"

    @model_validator(mode="after")
    def recording_requires_motion_id(self):
        if self.mode == GenerationMode.RECORDING and not self.motion_media_id:
            raise ValueError("Recording mode requires a driving motion media ID.")
        return self


class GenerationStatus(BaseModel):
    job_id: str
    state: JobState
    progress: float = Field(default=0.0, ge=0.0, le=1.0)
    message: str
