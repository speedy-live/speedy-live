# SPEEDY LIVE — AVTR-1 Portrait Engine Candidate Review

**Review date:** 2026-11-27  
**Decision:** Conditional private proof-of-concept candidate only. Not approved for customer use.  
**Scope:** Portrait/talking-head live path only. This is not a full-body animation solution.

## Why it is worth testing

The official AVTR-1 model card describes a local portrait-image plus dual-stream-audio pipeline (speech and listening track), with lip-synchronised output at 25 FPS. It publishes model artifacts and a local inference/streaming setup using CUDA 12.x, TensorRT 10.x, and Ampere-or-newer NVIDIA GPUs.

The model card reports per-five-frame-chunk latency:
- L40: 84 ms
- A100: 91 ms
- RTX 4060 Ti: 166 ms
- RTX 3070: 181 ms
- L4: 202 ms
- RTX 3060 Ti: 206 ms
- RTX 4060: 232 ms

A five-frame chunk at 25 FPS represents 200 ms. These are vendor-reported figures, not independently reproduced SPEEDY LIVE results. They suggest a plausible portrait benchmark target on selected GPUs, but do not establish end-to-end calling latency or product quality.

Official sources:
- Model card: https://huggingface.co/avaturn-live/avtr-1
- Code repository: https://github.com/avaturn-live/avtr-1
- Project page: https://avtr-1.avaturn.live/

## Important licensing blockers

The model card states:
- Model weights and avatar assets use the AVTR-1 Community License. It describes commercial use for entities below USD 10 million annual revenue, subject to Attachment A; entities at or above that threshold require a separate commercial agreement.
- The pipeline uses InsightFace SCRFD and 2D106 pretrained models, described as non-commercial research only. Commercial deployment requires a separate InsightFace commercial licence or replacement with permissively licensed alternatives.
- The Avaturn Streamer source directory is separately under PolyForm Noncommercial 1.0.0. Commercial use requires a separate Streamer Commercial License regardless of revenue.
- HuBERT, MODNet and the TensorRT plugin have separate third-party notices/Apache-2.0 terms.

Therefore:
1. Do not copy or use the Avaturn Streamer in a commercial SPEEDY LIVE deployment without a separate written licence.
2. Do not deploy the bundled InsightFace models commercially without a licence or replacement.
3. Before any commercial use, obtain and archive the complete AVTR-1 Community License including Attachment A and review every third-party notice and model artifact.
4. Confirm the licence permits our intended redistribution, hosting, customer usage, modification, and derivative deployment.
5. The public model card describes its training corpus as publicly available video content. It does not provide a complete per-asset consent audit in the reviewed material. Obtain written provenance/rights clarification; do not assume public availability means commercial training rights.

## Technical limitations and fit

- Portrait/talking-head only; does not satisfy full-body movement, arms, hands or legs.
- Input is described as a portrait and dual audio streams, not the current SPEEDY LIVE pose-event contract. An adapter and audio pipeline would be needed.
- The model card warns about near-frontal input assumptions, out-of-distribution poses, occlusion, heavy background noise, and subtle artifacts on long monologues.
- It is not proof of end-to-end WebRTC readiness. Network transport, audio capture, buffering, concurrency, GPU scheduling, and session lifecycle remain SPEEDY LIVE responsibilities.
- The reported benchmark table is vendor-provided and must be reproduced on the exact candidate hardware.

## Proposed private proof-of-concept gates

Proceed only after licensing and hardware checks are satisfied:

1. Download artifacts only into private, access-controlled model storage; never commit weights or customer media to Git.
2. Inventory every artifact and dependency with exact version, source, licence, and SHA-256.
3. Replace InsightFace with a commercially suitable detector/landmark solution or obtain a written licence.
4. Do not use the separately licensed noncommercial Avaturn Streamer; implement an independent SPEEDY LIVE adapter/streaming layer or obtain a commercial licence.
5. Run inference locally on a rented, time-limited test GPU before any recurring GPU spend.
6. Measure end-to-end portrait image/audio-to-frame latency, p50/p95, sustained FPS, dropped frames, VRAM, GPU cost, and concurrency.
7. Evaluate identity preservation, lip-sync, expression fidelity, silent listening behavior, long-session drift, and demographic/lighting robustness on consented held-out test subjects.
8. Keep full-body model evaluation separate.

## Current decision

AVTR-1 is the strongest newly identified portrait live-path candidate for a controlled private evaluation, but it is not selected as the final engine and is not commercially cleared for SPEEDY LIVE deployment. The licence restrictions on InsightFace and the Avaturn Streamer must be resolved first. No model download, GPU rental, customer release, or production deployment is authorized by this review.
