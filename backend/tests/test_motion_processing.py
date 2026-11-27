import pytest

from app.motion_processing import diagnose_motion_sequence, validate_motion_sequence
from app.schemas import FaceControls, Landmark, MotionFrame


def sample(sequence: int, timestamp: int) -> MotionFrame:
    return MotionFrame(
        sequence=sequence,
        timestamp_ms=timestamp,
        body_landmarks=[Landmark(x=0.5, y=0.5)],
        face=FaceControls(blendshapes={"eyeBlinkLeft": 0.95}),
    )


def test_diagnostics_measure_timing_without_smoothing() -> None:
    frames = [sample(0, 0), sample(1, 33), sample(2, 66), sample(3, 99)]
    result = diagnose_motion_sequence(frames)
    assert result.sample_count == 4
    assert result.duration_ms == 99
    assert result.median_interval_ms == 33
    assert result.estimated_fps == pytest.approx(30.303, rel=1e-3)
    assert result.body_point_count == 4


def test_blink_peak_is_preserved_in_original_samples() -> None:
    frames = [
        sample(0, 0),
        sample(1, 16),
        sample(2, 32),
    ]
    frames[1].face.blendshapes["eyeBlinkLeft"] = 1.0
    assert [frame.face.blendshapes["eyeBlinkLeft"] for frame in frames] == [
        0.95, 1.0, 0.95
    ]


def test_rejects_non_increasing_timestamps() -> None:
    with pytest.raises(ValueError, match="timestamps"):
        validate_motion_sequence([sample(0, 10), sample(1, 10)])


def test_rejects_non_increasing_sequence_numbers() -> None:
    with pytest.raises(ValueError, match="sequence"):
        validate_motion_sequence([sample(0, 0), sample(0, 16)])
