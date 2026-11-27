"""Deterministic motion-stream validation and timing diagnostics.

This module deliberately does not smooth or debounce signals. It preserves
short events (for example blinks) and reports timing/quality issues for later
training and real-time engine work.
"""
from dataclasses import dataclass
from statistics import median

from app.schemas import MotionFrame


@dataclass(frozen=True)
class MotionDiagnostics:
    sample_count: int
    duration_ms: int
    median_interval_ms: float
    estimated_fps: float
    max_gap_ms: int
    body_point_count: int
    left_hand_point_count: int
    right_hand_point_count: int
    face_sample_count: int


def validate_motion_sequence(frames: list[MotionFrame]) -> None:
    """Reject duplicate or out-of-order frame IDs/timestamps."""
    previous_sequence = -1
    previous_timestamp = -1
    for frame in frames:
        if frame.sequence <= previous_sequence:
            raise ValueError("Motion frame sequence must increase strictly.")
        if frame.timestamp_ms <= previous_timestamp:
            raise ValueError("Motion timestamps must increase strictly.")
        previous_sequence = frame.sequence
        previous_timestamp = frame.timestamp_ms


def diagnose_motion_sequence(frames: list[MotionFrame]) -> MotionDiagnostics:
    """Return descriptive timing/coverage metrics without altering input."""
    if not frames:
        return MotionDiagnostics(
            sample_count=0,
            duration_ms=0,
            median_interval_ms=0.0,
            estimated_fps=0.0,
            max_gap_ms=0,
            body_point_count=0,
            left_hand_point_count=0,
            right_hand_point_count=0,
            face_sample_count=0,
        )

    validate_motion_sequence(frames)
    intervals = [
        frames[index].timestamp_ms - frames[index - 1].timestamp_ms
        for index in range(1, len(frames))
    ]
    typical_interval = float(median(intervals)) if intervals else 0.0
    return MotionDiagnostics(
        sample_count=len(frames),
        duration_ms=frames[-1].timestamp_ms - frames[0].timestamp_ms,
        median_interval_ms=typical_interval,
        estimated_fps=1000.0 / typical_interval if typical_interval else 0.0,
        max_gap_ms=max(intervals, default=0),
        body_point_count=sum(len(frame.body_landmarks) for frame in frames),
        left_hand_point_count=sum(len(frame.left_hand_landmarks) for frame in frames),
        right_hand_point_count=sum(len(frame.right_hand_landmarks) for frame in frames),
        face_sample_count=sum(1 for frame in frames if frame.face is not None),
    )
