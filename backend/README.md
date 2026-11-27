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