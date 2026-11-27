# SPEEDY LIVE backend deployment and production connection

This service is a separate FastAPI container. Cloudflare Pages serves the Vite website; it does not run this Python API or provide the GPU inference runtime.

## Current release boundary

The API foundation can be deployed for health, readiness, engine status, and explicitly requested motion diagnostics. It is not a photo-animation service yet. No customer photo upload, media storage, animation inference, WebRTC calling, or recording endpoint is implemented. Keep customer animation disabled.

Do not set `ANIMATION_ENGINE_CUSTOMER_RELEASE_APPROVED=true` or invent a release approval ID to make the status look green. Those settings are only for a real reviewed engine release.

## Required deployment shape

1. Keep the existing customer website at `https://speedy-live.pages.dev`.
2. Deploy `backend/` as a Docker container on a server that supports long-running Python services. Use a GPU-capable machine only when a qualified inference model actually requires it.
3. Give the API a stable HTTPS origin, for example `https://api.<your-domain>`. The example is a placeholder, not a configured address.
4. Configure the API's `ALLOWED_ORIGINS` to include the exact customer website origin: `https://speedy-live.pages.dev`.
5. In the existing Cloudflare Pages project's production build environment, set `VITE_API_BASE_URL` to the real HTTPS API origin. This variable is public browser configuration; never put secrets in it.
6. Trigger a new Pages build after changing the build environment variable.
7. Verify `GET /health`, `GET /ready`, and `GET /engine/status` over HTTPS. A healthy API process is not proof that an animation engine is installed or operational.

## Backend environment

Minimum settings for an API-only deployment:

```text
ENVIRONMENT=production
ALLOWED_ORIGINS=https://speedy-live.pages.dev
ANIMATION_ENGINE=unconfigured
```

Keep model adapter paths empty until an approved local adapter and its verified model manifest are installed inside the backend's permitted local engine directory. Keep release approval false.

## Container

Build from the repository root:

```bash
docker build -f backend/Dockerfile -t speedy-live-ai ./backend
```

Run with the environment settings above and publish container port 8000 behind an HTTPS reverse proxy. Do not expose an unauthenticated inference or media endpoint to the public internet.

## Before accepting customer photos

Implement and security-test authentication, upload authorization, strict image decoding and size limits, private object storage, short-lived media URLs, deletion/retention controls, consent records, abuse limits, and audit logging. The current Photo Studio only previews a local browser object URL and does not upload the image.

## Before enabling portrait or full-body animation

For each mode separately, verify model and dependency licences for commercial use, checkpoint hashes, dataset provenance and consent, identity preservation, temporal stability, expression and lip-sync quality, latency, memory, throughput, safety, and rollback. Record the evidence and reviewers. Full-body capability must not be inferred from a portrait model.

## Before live calling and recording

Implement authenticated session signalling, WebRTC transport, audio/video synchronization, reconnect handling, recording consent, secure recording storage, access control, retention/deletion, and end-to-end load and security tests. These features are not present in the current API.

## Production rule

Do not merge or deploy experimental changes to the existing production website just because CI passes. CI checks the frontend build and backend tests; it does not deploy the website, host the API, install a model, or validate live calls. Promote only after the actual production deployment and end-to-end checks have been completed.
