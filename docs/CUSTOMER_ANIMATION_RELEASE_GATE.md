# SPEEDY LIVE — Customer Animation Release Gate

**Status:** Required release procedure. No animation engine is currently approved for customer use.

## Two independent gates

Customer animation is enabled only when BOTH conditions are true:

1. A local adapter and model artifact are registered and pass the adapter runtime self-test.
2. The release operator explicitly sets both environment variables:
   - `ANIMATION_ENGINE_CUSTOMER_RELEASE_APPROVED=true`
   - `ANIMATION_ENGINE_RELEASE_APPROVAL_ID=<review-record-id>`

The approval ID must identify a real, retained release-review record. A non-empty string is only a software switch; it is not proof that the review happened.

Keep the approval flag false or unset in development, staging, and production until the complete release review is signed off. Never set it just to make a demo endpoint return success.

## Required review evidence

The referenced review record must include:

- Exact engine/model ID and version.
- Immutable checkpoint SHA-256 matching the installed artifact.
- Source-code, checkpoint/weights, detector, dependency, and dataset commercial-rights review.
- Dataset consent audit and documented scope of use.
- Private benchmark results on a held-out, consented test set.
- Identity preservation, expression, lip-sync, temporal stability, and visual-quality review.
- Supported modes explicitly approved: portrait and full-body are separate decisions.
- Hardware, GPU memory, sustained throughput, p50/p95 latency, dropped frames, and cost measurements.
- Security, consent, abuse reporting, retention, and deletion review.
- Named reviewers, decision date, limitations, and rollback plan.

Do not approve live calling based on an offline recording benchmark. Do not approve full-body animation based on portrait-only results.

## Operational checks before approval

1. Confirm `/health` responds: this only proves the API process is alive.
2. Confirm `/ready` reports runtime health and customer animation state separately.
3. Confirm `/engine/status` identifies the exact installed model and version.
4. Confirm the adapter's health check performs a real, bounded inference self-test; it must not return success merely because files exist or the Python module imports.
5. Confirm `/engine/capabilities/{mode}` remains HTTP 503 until the explicit approval gate is satisfied.
6. Re-run the locked benchmark after any checkpoint, adapter, dependency, driver, or inference configuration change.

## Environment configuration

The backend reads these settings through Pydantic Settings:

- `ANIMATION_ENGINE_CUSTOMER_RELEASE_APPROVED` — boolean; defaults to false.
- `ANIMATION_ENGINE_RELEASE_APPROVAL_ID` — review record reference; defaults to empty.

Do not store secrets or private review evidence in Git. Use the deployment platform's protected environment-variable and access-control features when a release is eventually approved.

## Current decision

No trained photo-animation checkpoint, qualified inference adapter, or measured model benchmark is currently present in this repository. Therefore the release flag must remain disabled. The release gate is preventive infrastructure, not evidence that the product is ready.
