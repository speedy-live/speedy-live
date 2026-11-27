"""Pure generation-job lifecycle rules.

This module deliberately has no database or queue. It validates transitions for a
future authenticated, durable job service; it is not a job API or worker.
"""
from app.schemas import GenerationStatus, JobState


_ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.PREPROCESSING, JobState.CANCELLED, JobState.FAILED}),
    JobState.PREPROCESSING: frozenset({JobState.RUNNING, JobState.CANCELLED, JobState.FAILED}),
    JobState.RUNNING: frozenset({JobState.SUCCEEDED, JobState.CANCELLED, JobState.FAILED}),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


class JobTransitionError(ValueError):
    """Raised when a generation job attempts an invalid state transition."""


def validate_job_transition(current: GenerationStatus, next_status: GenerationStatus) -> None:
    """Validate identity, state progression and monotonic progress."""
    if current.job_id != next_status.job_id:
        raise JobTransitionError("A job transition cannot change the job ID.")

    if next_status.state not in _ALLOWED_TRANSITIONS[current.state]:
        raise JobTransitionError(
            f"Transition from {current.state.value} to {next_status.state.value} is not allowed."
        )

    if next_status.progress < current.progress:
        raise JobTransitionError("Job progress cannot move backwards.")

    if next_status.state == JobState.SUCCEEDED and next_status.progress != 1.0:
        raise JobTransitionError("A successful job must have progress equal to 1.0.")

    if next_status.state in {JobState.FAILED, JobState.CANCELLED}:
        if next_status.progress != current.progress:
            raise JobTransitionError("Failed or cancelled jobs must retain their last progress value.")
