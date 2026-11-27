import pytest
from pydantic import ValidationError

from app.schemas import (
    FaceControls,
    GenerationMode,
    GenerationRequest,
    JobState,
    Landmark,
    MotionFrame,
)


def test_landmark_accepts_normalized_coordinates() -> None:
    point = Landmark(x=0.25, y=0.75, z=0.1, visibility=0.9)
    assert point.x == 0.25
    assert point.visibility == 0.9


def test_landmark_rejects_coordinates_outside_normalized_frame() -> None:
    with pytest.raises(ValidationError):
        Landmark(x=1.5, y=0.2)


def test_motion_frame_has_sequence_and_timestamp() -> None:
    frame = MotionFrame(sequence=4, timestamp_ms=120, body_landmarks=[])
    assert frame.sequence == 4
    assert frame.timestamp_ms == 120


def test_recording_request_requires_driving_media() -> None:
    request = GenerationRequest(
        mode=GenerationMode.RECORDING,
        source_media_id="source-image-001",
        consent_record_id="consent-0001",
    )
    with pytest.raises(ValueError):
        request.validate_mode_requirements()


def test_live_request_does_not_require_driving_clip_id() -> None:
    request = GenerationRequest(
        mode=GenerationMode.LIVE,
        source_media_id="source-image-001",
        consent_record_id="consent-0001",
    )
    assert request.mode == GenerationMode.LIVE


def test_face_control_limits_rotation() -> None:
    with pytest.raises(ValidationError):
        FaceControls(yaw_degrees=180)


def test_job_states_are_explicit() -> None:
    assert JobState.QUEUED == "queued"
    assert JobState.SUCCEEDED == "succeeded"
