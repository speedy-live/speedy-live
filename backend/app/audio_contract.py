"""Validated audio inputs for model-agnostic, audio-driven portrait generation.

Payloads are bounded PCM chunks. Transport, authentication, media storage and
model-specific resampling remain separate responsibilities.
"""
import base64
import binascii
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


AudioEncoding = Literal["pcm_s16le", "pcm_f32le"]
SUPPORTED_SAMPLE_RATES = {16000, 24000, 44100, 48000}
MAX_AUDIO_CHUNK_BYTES = 256 * 1024


class AudioChunk(BaseModel):
    """One timestamped PCM chunk from a single participant audio track."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sequence: int = Field(ge=0)
    timestamp_ms: int = Field(ge=0)
    sample_rate_hz: int
    channels: Literal[1, 2] = 1
    encoding: AudioEncoding = "pcm_s16le"
    payload_base64: str = Field(min_length=4, max_length=349528)

    @field_validator("sample_rate_hz")
    @classmethod
    def validate_sample_rate(cls, value: int) -> int:
        if value not in SUPPORTED_SAMPLE_RATES:
            raise ValueError("Unsupported audio sample rate.")
        return value

    @model_validator(mode="after")
    def validate_pcm_payload(self):
        try:
            payload = base64.b64decode(self.payload_base64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Audio payload must be valid base64.") from exc

        if not payload or len(payload) > MAX_AUDIO_CHUNK_BYTES:
            raise ValueError("Audio chunk must contain between 1 byte and 256 KiB.")
        bytes_per_sample = 2 if self.encoding == "pcm_s16le" else 4
        if len(payload) % (bytes_per_sample * self.channels):
            raise ValueError("PCM payload length must align to sample size and channel count.")
        return self


class AudioDrivenPortraitRequest(BaseModel):
    """References to consented media for a portrait animation session."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    portrait_media_id: str = Field(min_length=8, max_length=128)
    speech_audio_media_id: str = Field(min_length=8, max_length=128)
    listening_audio_media_id: str | None = Field(default=None, min_length=8, max_length=128)
    consent_record_id: str = Field(min_length=8, max_length=128)
    output_format: Literal["mp4", "webm"] = "mp4"


def validate_audio_sequence(chunks: list[AudioChunk]) -> None:
    """Reject duplicate/out-of-order chunk IDs or timestamps."""
    previous_sequence = -1
    previous_timestamp = -1
    for chunk in chunks:
        if chunk.sequence <= previous_sequence:
            raise ValueError("Audio chunk sequence must increase strictly.")
        if chunk.timestamp_ms <= previous_timestamp:
            raise ValueError("Audio chunk timestamps must increase strictly.")
        previous_sequence = chunk.sequence
        previous_timestamp = chunk.timestamp_ms
