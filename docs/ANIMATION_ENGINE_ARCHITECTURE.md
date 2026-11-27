# SPEEDY LIVE — Animation Engine Architecture Decision

**Decision status:** Proposed engineering direction; no model has been approved for commercial deployment.  
**Date:** 2026-11-27  
**Branch:** ai-backend-foundation

## Executive decision

Build SPEEDY LIVE as an engine-independent product with two generation paths:

1. **Portrait live path (first technical milestone):** a streaming, identity-preserving photo animation engine driven by timestamped face controls and audio. This is the first path to prototype because it is the narrowest route to a usable live demo.
2. **Full-body path (second technical milestone):** a separate image-conditioned human animation engine driven by synchronized body and hand motion. It must preserve clothing, anatomy, identity, and temporal consistency. Do not claim this is solved by the portrait engine.

The customer experience should eventually unify both paths, but their models, quality gates, and hardware profiles must remain independently measurable.

## Candidate review and licensing decision

### PersonaLive — do not adopt for commercial use at present

The official repository describes PersonaLive as a real-time, streamable portrait animation framework and advertises a streaming path. However, its README explicitly states that the project is for academic research only. An Apache-2.0 repository badge does not override a more restrictive project-level use condition or grant rights to every checkpoint and dependency.

**Decision:** research reference only. Do not copy its weights or integrate its code into a paid SPEEDY LIVE product unless the authors provide written commercial permission covering the exact code, checkpoints, and dependencies.

Official source: https://github.com/GVCLab/PersonaLive

### LiveAnimate — monitor, do not depend on it

LiveAnimate is relevant to pose-driven human animation and streaming, but the previously reviewed official project status indicated that implementation code was not yet generally available. It cannot be the foundation of a build until source, weights, dependencies, and commercial terms can all be inspected.

Official sources:
- https://liveanimate.github.io/
- https://github.com/liveanimate/LiveAnimate

### LivePortrait — limited research reference

LivePortrait is relevant to portrait motion transfer, but it is not a full-body solution. Its code licence does not automatically clear every bundled face detector or pretrained model for commercial use. Any future evaluation must replace or separately clear restricted components.

Official source: https://github.com/KlingAIResearch/LivePortrait

### General rule

No candidate is approved merely because its GitHub repository displays MIT, Apache, or another open-source licence. Before adoption, record separate rights for:
- source code and model architecture implementation;
- each pretrained checkpoint and base model;
- face/pose/hand detectors and other dependencies;
- training, validation, and evaluation datasets;
- generated outputs and any applicable third-party terms.

## Target system layout

```text
Web client (React / Vite)
  ├─ camera + microphone capture
  ├─ current face / pose / hand tracking
  ├─ timestamped control stream
  ├─ recording studio controls
  └─ WebRTC sender (later milestone)
          |
          v
SPEEDY LIVE API (FastAPI)
  ├─ authentication and consent
  ├─ upload / media lifecycle
  ├─ job and session orchestration
  ├─ quota / usage metering
  └─ engine adapter interface
          |
          +-----------------------------+
          |                             |
          v                             v
Portrait GPU worker              Full-body GPU worker
(streaming portrait)             (pose-driven video)
          |                             |
          +--------------+--------------+
                         v
              private output storage
                         |
             recording download / WebRTC
```

Cloudflare Pages remains the web delivery layer; it is not the place to run diffusion or other large GPU models. GPU workers should be independently deployable and scale to zero when practical. Do not rent a continuously running GPU before there is a measured workload.

## Engine adapter contract

The API must not be coupled to one model vendor or research repository. Each engine adapter must declare:
- supported mode: portrait, full_body, or both;
- supported input controls and media formats;
- model ID, version, checkpoint hash, and licence audit reference;
- hardware requirements and precision mode;
- whether it supports streaming or only offline jobs;
- health/readiness and warm-up state;
- output frame format, resolution, frame rate, and audio policy;
- cancellation, timeout, and resource cleanup behavior.

A model that only generates a finished video must never be advertised as real-time calling.

## Build sequence

### Phase A — contract and local test harness
- Keep the existing API schemas and unconfigured engine safe by default.
- Define explicit portrait and full-body engine capabilities.
- Define a deterministic fake engine for API integration tests only; label all output as synthetic test data.
- Add contract tests for engine readiness, unsupported modes, cancellation, and model metadata.
- No GPU dependency or production deployment in this phase.

### Phase B — portrait proof of concept
- Select one candidate only after component-by-component commercial rights review.
- Run a private benchmark on a consented, held-out set.
- Measure identity stability, blink/expression fidelity, speech lip-sync, end-to-end latency, sustained FPS, VRAM and cost.
- Start with recording/offline generation if the real-time candidate cannot meet the measured target.
- Keep webcam driving separate from the uploaded identity image.

### Phase C — full-body proof of concept
- Evaluate full-body models independently.
- Test hands, fingers, occlusion, turning, walking, clothing stability and long-sequence drift.
- Do not extrapolate portrait results to full-body capability.
- Require a commercially cleared checkpoint and training-data provenance before fine-tuning.

### Phase D — calling and commercial operations
- Add WebRTC only after the streaming engine has stable output and measurable latency.
- Add per-minute metering from actual GPU and storage cost.
- Price tiers only after measuring cost at realistic concurrency.
- Add consent confirmation, impersonation safeguards, reporting, retention and deletion controls before public launch.

## Explicit non-goals for this decision

- No third-party hosted animation API.
- No recurring external animation API charge.
- No automatic production deployment.
- No model weights or datasets committed to Git.
- No claim that current MediaPipe tracking animates the uploaded photo.
- No claim of full-body, live-call, or commercial readiness before the relevant tests pass.

## Acceptance criteria before selecting a production model

A candidate may move to a private proof of concept only when:
1. Code, weights, detectors, dependencies, and datasets have documented compatible commercial rights.
2. A runnable inference implementation and exact checkpoint are available.
3. Hardware requirements are confirmed on a rented test GPU before ongoing spend.
4. The candidate can accept the SPEEDY LIVE control contract or has a documented adapter plan.
5. The evaluation set and pass thresholds are agreed before testing.

## Current honest baseline

SPEEDY LIVE currently captures motion controls and validates dataset/model/benchmark metadata. It does not yet have a trained photo-animation model, GPU inference worker, production media upload, or WebRTC calling. This decision document defines the route; it is not evidence that those capabilities have been built.
