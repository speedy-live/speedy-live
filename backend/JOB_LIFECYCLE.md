# Generation job lifecycle contract

`app/job_lifecycle.py` defines the allowed state transitions for a future generation service:

- queued → preprocessing, cancelled, or failed
- preprocessing → running, cancelled, or failed
- running → succeeded, cancelled, or failed
- succeeded, failed, and cancelled are terminal states

Progress cannot move backwards. A successful job must report 100% progress. Failed and cancelled jobs preserve the last completed progress value. A transition cannot change the job ID.

This is a pure validation layer only. It does not create jobs, persist state, schedule GPU work, authenticate users, authorize media, or provide cancellation of running inference. Do not expose it as a working generation API until a durable database-backed job service, authenticated ownership checks, worker queue, idempotency, retry policy, timeouts, and output storage are implemented.
