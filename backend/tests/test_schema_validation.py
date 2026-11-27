import pytest
from pydantic import ValidationError

from app.schemas import (
    FaceControls,
    GenerationMode,
    GenerationRequest,
    HandLandmarks,
    Landmark,
    MotionFrame,
)


def test_blendshape_scores_must_be_between_zero_and_one() -> None:
    with pytest.raises(ValidationError):
        FaceControls(blendshapes={"eyeBlinkLeft": 1.2})


def test_valid_blink_score_is_preserved() -> None:
    face = FaceControls(blendshapes={"eyeBlinkLeft": 0.98})
    assert face.blendshapes["eyeBlinkLeft"] == 0.98


def test_motion_frame_preserves_both_hand_landmark_sets() -> None:
    points = [Landmark(x=0.4, y=0.6) for _ in range(21)]
    frame = MotionFrame(
        sequence=0,
        timestamp_ms=0,
        hands=[
            HandLandmarks(handedness="Left", landmarks=points),
            HandLandmarks(handedness="Right", landmarks=points),
        ],
    )
    assert len(frame.hands) == 2
    assert len(frame.hands[0].landmarks) == 21
    assert frame.hands[1].handedness == "Right"


def test_recording_request_requires_motion_media_id() -> None:
    with pytest.raises(ValidationError):
        GenerationRequest(
            mode=GenerationMode.RECORDING,
            source_media_id="source-image-01",
            consent_record_id="consent-record-01",
        )


def test_live_request_can_omit_motion_media_id() -> None:
    request = GenerationRequest(
        mode=GenerationMode.LIVE,
        source_media_id="source-image-01",
        consent_record_id="consent-record-01",
    )
    assert request.motion_media_id is None
