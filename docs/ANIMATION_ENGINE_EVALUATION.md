# Animation engine evaluation — 27 November 2026

## Decision summary

Do not connect a model to the customer-facing product until it passes commercial-rights review and an actual GPU/browser acceptance test.

### Candidate A: Motion Mirror + Wan2.1-VACE

Repository: https://github.com/halli75/motion-mirror

**Best current candidate for a first recording-studio experiment, not live calling.**

The project accepts a character image plus a prerecorded driving video and generates a new video. Its documented pipeline segments the character, extracts 133 whole-body keypoints (including hands and face), conditions Wan2.1-VACE, and passes through the driving video's audio.

Documented hardware estimates:
- Wan 1.3B: about 9 GB free VRAM (the backend table reports 8 GB measured); lower identity fidelity and possible appearance drift.
- Wan 14B GGUF: about 18 GB free VRAM; described as stronger identity retention.
- 32 GB system RAM and roughly 20 GB cache for 1.3B; 40 GB RAM and roughly 45 GB cache for 14B GGUF.
- NVIDIA CUDA 12.x / driver 570+ are listed as validated.
- CPU-only actual generation is not supported; CPU offload can make an 81-frame clip take tens of minutes.

Licensing notes from the project's third-party licence inventory:
- Motion Mirror code: MIT.
- Wan2.1-VACE 1.3B and 14B weights: listed as Apache 2.0.
- DWPose, rembg/U2-Net, and optional SAM-2 components are listed as Apache 2.0.
- The 1.3B fast distillation LoRA is CC-BY-NC-SA-4.0 and is explicitly non-commercial. Do not use it for SPEEDY LIVE.
- The 14B LightX2V fast LoRA is listed as Apache 2.0.
- The experimental FusionX GGUF fast artifact is not yet validated through the project's Diffusers path.

Important limitations:
- This is offline/reference-video motion transfer, not a real-time webcam-to-photo animation system.
- Its README currently says example generations are coming soon. The project is alpha.
- It does not by itself provide the low-latency, continuously streaming, WebRTC output required for live calls.
- Its generated output and identity quality must be independently tested on representative consented images and motions.
- Review upstream Wan acceptable-use terms and every model/dependency licence at the time of deployment; this document is not legal advice.

**Proposed use:** isolate it as an experimental recording-studio worker. Do not expose it as a production feature until benchmarked and accepted.

### Candidate B: LiveAnimate

Repository: https://github.com/liveanimate/LiveAnimate  
Project page: https://liveanimate.github.io/

The paper/project page describes single-image, pose-stream-conditioned full-body animation with stable long-form output, reporting about 19.63 FPS on two NVIDIA H100 GPUs.

However, the public repository currently contains only a README and assets and says inference/training code is coming soon. Therefore it is not currently an installable backend we can integrate. Two H100 GPUs are also a significant operating cost.

**Proposed use:** monitor for a public inference release and then reassess. Do not base the current implementation on unavailable code.

### Candidate C: LivePortrait

Repository: https://github.com/KlingAIResearch/LivePortrait

Useful as a possible face/portrait component, but it is not a full-body motion solution. Its model/detector weight licensing needs a component-by-component commercial review. It cannot satisfy the whole SPEEDY LIVE product on its own.

## Product architecture decision

Keep two separate execution paths:

1. **Recording studio:** image + recorded driving clip -> asynchronous GPU generation job -> preview/export. Motion Mirror is the first experimental candidate.
2. **Live calls:** camera pose/expression/audio stream -> genuinely streaming image animation engine -> WebRTC video track. This remains blocked until a suitable streaming engine is available and validated. Do not route live calls through a batch clip generator.

The browser MediaPipe tracker remains a control-signal source only. It does not animate the uploaded photograph.

## Acceptance tests before any customer launch

- Identity: same person's face, hair, clothing, body proportions and appearance remain recognisable across the whole clip.
- Movement: full-body motion follows the driver; hands/fingers and feet do not disappear or deform severely.
- Face: blink, gaze, smile/frown and mouth motion are plausible and temporally aligned.
- Audio: original speech remains synchronised; no invented speech when the driver is silent.
- Stability: no unacceptable flicker, jitter, duplicated limbs, background leakage or identity drift.
- Performance: measure end-to-end generation time, startup time, VRAM, RAM, throughput and cost per minute of output on the exact rented GPU.
- Safety/privacy: authenticated consent, private temporary storage, retention/deletion, file validation, quotas and audit events.
- Legal: verify licences for code, every weight, detector, segmentation model, adapter/LoRA and output use before commercial release.

## Current implementation status

No animation model is installed or running. No upload/inference endpoint is exposed. No GPU has been provisioned. The API health endpoint only proves the Python process can respond.
