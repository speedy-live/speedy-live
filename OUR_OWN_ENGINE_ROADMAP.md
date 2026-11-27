# SPEEDY LIVE — Our Own Animation Engine Roadmap

## Product and ownership rule

SPEEDY LIVE will not depend on a third-party hosted animation API, paid per-minute inference API, or another company's live-avatar service. Customer photos, driving video, motion signals, and generated outputs will be processed by infrastructure that we control.

The long-term objective is to own the animation engine: its data pipeline, training/evaluation code, model adaptations, inference runtime, serving logic, and product integration.

We may study public research, papers, open-source implementations, and legally usable model weights as engineering references or temporary research baselines. That does **not** make a third-party hosted API part of the product. Any external model weights used during development must have verified terms compatible with our intended use. We will not copy code or weights with incompatible licences, and we will not claim a model trained by someone else is our original model.

## What "our own engine" means

We will build and own these layers:

1. **Capture and control:** browser camera capture, face expression, head pose, body pose, hands, audio timing, calibration and motion smoothing.
2. **Data pipeline:** consented image/video collection, identity-safe preprocessing, pose/face/audio annotations, quality checks, secure dataset storage and deletion.
3. **Model research and training:** architecture experiments, training scripts, fine-tuning where permitted, evaluation, checkpoints and model versioning.
4. **Inference runtime:** our own Python/PyTorch runtime, GPU scheduling, streaming frame pipeline, batching, memory management and health monitoring.
5. **Temporal consistency:** identity preservation, body/hand continuity, face expression control, flicker reduction and realistic motion constraints.
6. **Product delivery:** private photo handling, recording/export, and later WebRTC video output.

## Build strategy — staged, not pretending

### Phase 0 — engineering foundation
- Keep the AI service separate from the Vite website.
- Define stable internal interfaces for image input, motion controls, generation jobs and output streams.
- Add unit tests and CI.
- No customer image upload or inference is enabled yet.

### Phase 1 — offline research prototype
- Use a locally run, legally compatible research baseline only to understand pose conditioning and video generation.
- No external hosted inference API.
- Build our own preprocessing, job lifecycle, output validation and evaluation harness.
- Compare the generated person against the reference identity and driving motion.
- This is a research baseline, not the SPEEDY LIVE engine and not a customer feature.

### Phase 2 — owned model adaptation
- Establish a consented, licensed training/validation dataset.
- Train or adapt motion-conditioning modules and identity-preservation components.
- Keep a complete record of dataset provenance, model lineage, licences and evaluation results.
- Train on rented GPU machines only when needed; store checkpoints and shut compute down between experiments.

### Phase 3 — our recording engine
- Implement image + recorded motion video -> generated video.
- Add quality gates, retries, job status, preview and download.
- Test identity, full-body movement, face, hands, audio sync, temporal stability, latency and cost.
- Do not launch until the output meets agreed quality criteria.

### Phase 4 — real-time engine
- Research a streaming architecture separately from offline diffusion generation.
- Convert browser tracking signals into a stable low-latency control stream.
- Build a continuously running frame generator and WebRTC output track.
- Measure end-to-end latency and dropped frames under realistic network/GPU load.
- Offline clip generation must never be represented as live calling.

### Phase 5 — train more of the model ourselves
- As data, budget and compute permit, replace research-baseline components with SPEEDY LIVE-trained components.
- Maintain reproducible training, checkpoint provenance and independent validation.
- Full foundation-model training from random initial weights is a much larger undertaking and is not assumed to be the first milestone.

## Compute and cost principles

- No permanently running GPU server during early development.
- Use on-demand GPU instances for training and batch generation experiments.
- Start with small, controlled experiments before expensive multi-GPU training.
- Record GPU type, VRAM, runtime, storage, energy/compute cost and output quality for every benchmark.
- Never promise low customer pricing until measured infrastructure cost per generated minute is known.
- Cloudflare Pages serves the frontend; it is not the GPU inference environment.

## Data, consent and privacy

- Use only images and videos the contributor owns or has explicit permission to use.
- Do not scrape people’s photographs or videos for training.
- Obtain separate, informed consent for any use of customer uploads in model training; default is no training use.
- Keep customer media private, encrypted in transit and at rest, access-controlled and retained only as long as needed.
- Provide deletion workflows for source media, generated media and derived data where applicable.
- Build dataset provenance and consent records before collecting any training data.

## Non-negotiable acceptance gates

A model is not ready because it produces a moving video. It must pass:
- identity consistency across frames;
- realistic and coordinated body movement;
- face expression and mouth/audio synchronisation;
- hand/finger and foot stability;
- no severe flicker, duplicate limbs, body warping or background artifacts;
- measurable performance on declared GPU hardware;
- documented model/data/dependency rights;
- security, privacy and abuse testing.

## Current status (27 November 2026)

- Separate FastAPI backend foundation exists on the development branch.
- Health/readiness endpoints and CI tests exist.
- No animation model is installed or running in this repository.
- No customer upload, inference, recording or WebRTC endpoint is enabled.
- No GPU instance has been provisioned.
- No SPEEDY LIVE model has been trained yet.

The next deliverable is an internal research harness and architecture interfaces, followed by a small local/offline baseline experiment. It is not a public customer feature.
