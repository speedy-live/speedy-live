import pytest

from app.job_lifecycle import JobTransitionError, validate_job_transition
from app.schemas import GenerationStatus, JobState


def status(state, progress):
    return GenerationStatus(
        job_id="generation_job_0001",
        state=state,
        progress=progress,
        message="test",
    )


def test_job_can_move_from_queue_to_preprocessing_to_running():
    validate_job_transition(status(JobState.QUEUED, 0), status(JobState.PREPROCESSING, 0.1))
    validate_job_transition(status(JobState.PREPROCESSING, 0.1), status(JobState.RUNNING, 0.4))


def test_success_requires_complete_progress():
    with pytest.raises(JobTransitionError, match="progress equal to 1.0"):
        validate_job_transition(status(JobState.RUNNING, 0.9), status(JobState.SUCCEEDED, 0.9))

    validate_job_transition(status(JobState.RUNNING, 0.9), status(JobState.SUCCEEDED, 1.0))


def test_progress_cannot_move_backwards_or_change_job_identity():
    with pytest.raises(JobTransitionError, match="backwards"):
        validate_job_transition(status(JobState.RUNNING, 0.5), status(JobState.RUNNING, 0.4))

    other = GenerationStatus(
        job_id="different_job_0002",
        state=JobState.RUNNING,
        progress=0.6,
        message="test",
    )
    with pytest.raises(JobTransitionError, match="job ID"):
        validate_job_transition(status(JobState.RUNNING, 0.5), other)


def test_terminal_job_cannot_be_restarted_or_cancelled_twice():
    with pytest.raises(JobTransitionError, match="not allowed"):
        validate_job_transition(status(JobState.SUCCEEDED, 1.0), status(JobState.RUNNING, 1.0))

    with pytest.raises(JobTransitionError, match="not allowed"):
        validate_job_transition(status(JobState.CANCELLED, 0.2), status(JobState.CANCELLED, 0.2))


def test_failed_job_preserves_last_progress():
    with pytest.raises(JobTransitionError, match="retain"):
        validate_job_transition(status(JobState.RUNNING, 0.4), status(JobState.FAILED, 0.5))

    validate_job_transition(status(JobState.RUNNING, 0.4), status(JobState.FAILED, 0.4))
