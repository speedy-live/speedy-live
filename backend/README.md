# SPEEDY LIVE AI backend

This folder is a separate Python service foundation. It is **not** an animation engine yet and must not be presented to customers as one.

## Current status

- FastAPI application scaffold.
- Health and readiness endpoints.
- Configuration is supplied through environment variables.
- No photo upload, storage, inference, recording, or WebRTC endpoint is enabled.
- Readiness reports that the animation engine is not configured until a real, commercially licensed model and runtime have been selected and tested.

## Local development

Requires Python 3.11 or newer.

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

Check:
- `GET /health` — process is responding.
- `GET /ready` — reports whether the animation engine is configured.

## Ownership direction

SPEEDY LIVE will not call a third-party hosted animation API. The long-term goal is an engine we own and operate: capture/control, data pipeline, model adaptation/training, inference runtime and streaming delivery. Public research and legally compatible model weights may be studied as internal baselines, but must not be misrepresented as our original model. See `../docs/OUR_OWN_ENGINE_ROADMAP.md`.

## Deployment direction

Deploy this service separately from the Vite website, on an on-demand GPU-capable host when inference is ready. Keep the GPU provider replaceable. Do not put model weights or secrets in the frontend repository.

Before enabling customer uploads, implement authenticated upload authorization, strict image validation, private object storage, short-lived access URLs, retention/deletion controls, abuse limits, and consent checks. Before enabling inference, document and verify commercial rights for every model weight, detector, dependency, and dataset-derived component.

## Product milestones

1. **Foundation (this commit):** API process, configuration, health/readiness.
2. **Model qualification:** compare candidate engines on identity preservation, full-body movement, face expressions, lip-sync, latency, GPU memory/cost, and commercial licensing.
3. **Private photo pipeline:** consent, secure upload, job lifecycle, deletion.
4. **Animation runtime:** real model inference with measurable quality and performance.
5. **Media output:** recording/export and WebRTC-compatible stream.
6. **Production hardening:** authentication, quotas, monitoring, autoscaling, security and load testing.

A healthy API process does not mean photo animation works.
## Website-to-backend connection

The Vite website can read `GET /ready` and submit an explicitly requested motion-only diagnostic to `POST /motion/diagnostics`. This diagnostic accepts up to 3,000 timestamped landmark samples and returns capture-quality measurements; it does not upload a photograph or video, save customer media, or run animation inference.

For local development, run the API at `http://localhost:8000` and set the frontend environment variable `VITE_API_BASE_URL=http://localhost:8000` before building the Vite app. Set the backend `ALLOWED_ORIGINS` to the exact website origin (scheme and hostname, no path), for example `http://localhost:5173`. For a deployed frontend, configure its build environment with the separately deployed API base URL, and configure the API's `ALLOWED_ORIGINS` with that deployed frontend origin. Do not put backend secrets in Vite variables; Vite variables are public in the browser bundle.

If `VITE_API_BASE_URL` is omitted, the website uses its own origin and therefore requires the API to be reverse-proxied under that same origin. A static Pages deployment alone does not host this FastAPI service.
