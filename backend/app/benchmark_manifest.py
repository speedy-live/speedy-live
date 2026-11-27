"""Validation for reproducible SPEEDY LIVE model benchmark records."""
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator


class BenchmarkMetrics(BaseModel):
    identity_similarity_mean: float | None = Field(default=None, ge=0, le=1)
    lip_sync_offset_ms_p50: float | None = Field(default=None, ge=0)
    head_motion_mae_degrees: float | None = Field(default=None, ge=0, le=180)
    body_pose_error: float | None = Field(default=None, ge=0)
    hand_pose_error: float | None = Field(default=None, ge=0)
    temporal_flicker_score: float | None = Field(default=None, ge=0)
    generated_fps: float | None = Field(default=None, gt=0, le=1000)
    latency_p50_ms: float | None = Field(default=None, ge=0)
    latency_p95_ms: float | None = Field(default=None, ge=0)
    dropped_frame_rate: float | None = Field(default=None, ge=0, le=1)
    peak_vram_mb: int | None = Field(default=None, gt=0)
    cost_per_output_minute_usd: float | None = Field(default=None, ge=0)


class BenchmarkRecord(BaseModel):
    benchmark_id: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9._-]+$")
    model_id: str = Field(min_length=3, max_length=80)
    model_version: str = Field(min_length=1, max_length=40)
    checkpoint_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    dataset_id: str = Field(min_length=3, max_length=100)
    dataset_version: str = Field(min_length=1, max_length=40)
    split: Literal["validation", "testing"]
    evaluated_at: str = Field(min_length=10, max_length=40)
    hardware: str = Field(min_length=2, max_length=160)
    runtime: str = Field(min_length=2, max_length=120)
    sample_count: int = Field(gt=0)
    metrics: BenchmarkMetrics
    notes: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def validate_benchmark(self):
        if self.metrics.latency_p50_ms is not None and self.metrics.latency_p95_ms is not None:
            if self.metrics.latency_p95_ms < self.metrics.latency_p50_ms:
                raise ValueError("p95 latency cannot be lower than p50 latency.")
        return self


class BenchmarkRecordError(ValueError):
    """Raised when a benchmark record is invalid."""


def validate_benchmark_record_json(raw_json: str) -> BenchmarkRecord:
    """Parse a benchmark record; validation does not certify the underlying measurements."""
    try:
        return BenchmarkRecord.model_validate_json(raw_json)
    except ValidationError as exc:
        raise BenchmarkRecordError(f"Invalid benchmark record: {exc}") from exc
