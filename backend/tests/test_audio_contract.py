import base64

import pytest
from pydantic import ValidationError

from app.audio_contract import AudioChunk, AudioDrivenPortraitRequest, validate_audio_sequence


def chunk(sequence: int, timestamp: int, payload: bytes = b"\\x00\\x00") -> AudioChunk:
    return AudioChunk(
        sequence=sequence,
        timestamp_ms=timestamp,
        sample_rate_hz=16000,
        channels=1,
        encoding="pcm_s16le",
        payload_base64=base64.b64encode(payload).decode("ascii"),
    )


def test_accepts_valid_mono_pcm_audio_chunk():
    value = chunk(0, 0)
    assert value.sequence == 0
    assert value.sample_rate_hz == 16000


def test_accepts_stereo_float_pcm_when_payload_is_aligned():
    value = AudioChunk(
        sequence=0,
        timestamp_ms=0,
        sample_rate_hz=48000,
        channels=2,
        encoding="pcm_f32le",
        payload_base64=base64.b64encode(b"\\x00" * 8).decode("ascii"),
    )
    assert value.channels == 2


@pytest.mark.parametrize("rate", [8000, 11025, 96000])
def test_rejects_unsupported_sample_rate(rate):
    with pytest.raises(ValidationError, match="Unsupported audio sample rate"):
        AudioChunk(
            sequence=0,
            timestamp_ms=0,
            sample_rate_hz=rate,
            payload_base64=base64.b64encode(b"\\x00\\x00").decode("ascii"),
        )


def test_rejects_invalid_base64():
    with pytest.raises(ValidationError, match="valid base64"):
        AudioChunk(
            sequence=0,
            timestamp_ms=0,
            sample_rate_hz=16000,
            payload_base64="not-base64!",
        )


def test_rejects_pcm_payload_not_aligned_to_sample_width():
    with pytest.raises(ValidationError, match="align"):
        chunk(0, 0, b"x")


def test_rejects_audio_chunk_over_size_limit():
    with pytest.raises(ValidationError, match="256 KiB"):
        chunk(0, 0, b"x" * (256 * 1024 + 2))


def test_validates_audio_chunk_sequence_and_timestamps():
    validate_audio_sequence([chunk(0, 0), chunk(1, 20)])
    with pytest.raises(ValueError, match="sequence"):
        validate_audio_sequence([chunk(0, 0), chunk(0, 20)])
    with pytest.raises(ValueError, match="timestamps"):
        validate_audio_sequence([chunk(0, 20), chunk(1, 20)])


def test_audio_driven_request_requires_consent_and_media_references():
    request = AudioDrivenPortraitRequest(
        portrait_media_id="portrait-asset-001",
        speech_audio_media_id="speech-asset-001",
        listening_audio_media_id="listening-asset-001",
        consent_record_id="consent-record-001",
    )
    assert request.listening_audio_media_id == "listening-asset-001"


def test_audio_driven_request_rejects_short_media_reference():
    with pytest.raises(ValidationError):
        AudioDrivenPortraitRequest(
            portrait_media_id="short",
            speech_audio_media_id="speech-asset-001",
            consent_record_id="consent-record-001",
        )
