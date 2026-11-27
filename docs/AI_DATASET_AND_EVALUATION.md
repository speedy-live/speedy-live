# SPEEDY LIVE — Training Data and Model Evaluation Standard

**Status:** Engineering specification — not evidence that a trained animation model exists.  
**Applies to:** Portrait animation, full-body animation, recording generation, and real-time generation.

This standard is the gate between collecting media and using it to train or evaluate a commercial SPEEDY LIVE model. A dataset or model must not be described as commercially cleared merely because its files are accessible or its code is open source.

## 1. Non-negotiable data rights

Every source asset must have a traceable rights record before it enters a training or evaluation set.

Required per asset:
- **asset_id:** unique, stable identifier; never use a person's name as the ID.
- **source_type:** image, video, or audio.
- **source_reference:** internal storage reference or documented source.
- **subject_id:** pseudonymous person/performer identifier, consistent across that person's assets.
- **consent_record_id:** reference to the signed/recorded permission.
- **permitted_purposes:** explicit list such as training, validation, testing, commercial_generation.
- **commercial_use_allowed:** explicit boolean supported by the actual agreement/licence.
- **retention_until** and **deletion_status**.
- **collected_at** and **reviewed_at**.

Rules:
1. Do not scrape faces, videos, voices, or motion data from social media.
2. Do not use a customer's uploaded photo or recording for model training by default. Training consent must be separate, optional, informed, and revocable where legally required.
3. A consent checkbox is not enough on its own: retain the underlying consent text/version, timestamp, subject or authorized representative, and scope.
4. Keep dataset records and consent evidence access-controlled. Do not put personal data, raw media, or secrets in Git.
5. If rights are unclear, exclude the asset. Do not infer commercial permission.
6. Maintain a deletion workflow that removes an asset from active datasets and records which dataset/model versions used it. Model unlearning may not be assumed; disclose limitations and obtain legal review where required.
7. Minors and sensitive contexts require a separate legal and safety review; exclude them from initial collection unless explicitly approved.

## 2. Dataset manifest contract

Use one JSON manifest per dataset release. The following is an illustrative shape, not a real dataset:

```json
{
  "dataset_id": "speedy-live-motion-v1",
  "version": "0.1.0",
  "purpose": "training",
  "commercial_use_allowed": false,
  "consent_audit_verified": false,
  "created_at": "YYYY-MM-DD",
  "assets": [
    {
      "asset_id": "asset_000001",
      "subject_id": "subject_0001",
      "source_type": "video",
      "source_reference": "private://dataset/asset_000001",
      "consent_record_id": "consent_000001",
      "permitted_purposes": ["training"],
      "commercial_use_allowed": false,
      "sha256": "64-character-lowercase-sha256",
      "media": {
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "duration_ms": 12000,
        "audio_present": true
      },
      "annotations": {
        "face_visible": true,
        "body_visibility": "full",
        "left_hand_visible": true,
        "right_hand_visible": true,
        "occlusion": "none",
        "camera_view": "front"
      }
    }
  ]
}
```

The example deliberately has both commercial flags set to false. Replace them only after a documented rights review; never copy the example as proof of clearance.

### Dataset quality and split rules

- Split by subject_id, not by frame or clip. One person must not appear in both training and held-out test sets.
- Keep a locked test set that model developers cannot tune against.
- Track front/side/three-quarter views, lighting, skin tones, clothing, backgrounds, camera distances, motion ranges, and accessibility needs to reveal coverage gaps.
- Record frame rate, resolution, duration, audio presence, missing frames, and annotation confidence.
- Include synchronized audio/video examples for lip-sync evaluation, with explicit voice and performance rights.
- Label occlusion and out-of-frame body parts; do not pretend invisible joints are ground truth.
- Deduplicate near-identical frames and clips; preserve source hashes and provenance.
- Keep validation and test assets in separate access-controlled locations from training assets.

## 3. Evaluation protocol

Evaluate portrait and full-body models separately. Report results by scenario and by relevant demographic/recording-condition slices, while protecting privacy. Do not publish a single average that hides severe failures.

| Dimension | What to measure | Required reporting |
|---|---|---|
| Identity preservation | Face/identity similarity against the reference identity over generated frames | Mean, median, lower-tail result, failure rate; document evaluator/model and its licence |
| Lip synchronisation | Audio-to-mouth timing and phoneme/viseme alignment | Offset distribution in milliseconds and a recognised sync score where valid |
| Expression fidelity | Agreement between driver expression controls and generated expression | Per-expression precision/recall or correlation; silent-mouth false-activation rate |
| Head motion | Yaw, pitch, and roll tracking error | Mean absolute angular error in degrees and tracking-loss rate |
| Body motion | Joint/pose error against held-out driving motion | Per-joint error, visible-joint coverage, and failure rate |
| Hands | Hand-joint error and finger visibility/continuity | Per-hand and per-finger error; occlusion-aware coverage |
| Temporal quality | Flicker, warping, identity drift, and frame-to-frame instability | Human-rated failure categories plus reproducible temporal metrics |
| Visual quality | Realism, anatomy, clothing/background stability | Blind human review with rubric, sample count, and confidence intervals |
| Real-time performance | End-to-end capture-to-render latency and sustained throughput | p50/p95 latency, generated FPS, dropped-frame rate, test device/GPU and network |
| Operating cost | GPU time and storage/egress per output minute | Measured cost per generated minute, hardware type, utilisation, and workload |

### Mandatory test scenarios

1. Neutral face, then blink, smile, frown, eyebrow raise, and speech.
2. Silent driver: generated mouth must remain appropriately still.
3. Slow and fast head turns, tilt, and return to neutral.
4. Upper-body gestures, arms crossing, hands entering/leaving frame, and finger articulation.
5. Full-body movement with turns, steps, and partial occlusion.
6. Low light, bright backlight, glasses, varied backgrounds, and camera movement.
7. Long recording to expose identity drift, flicker, and accumulated timing error.
8. Network and GPU load tests for live mode.

## 4. Benchmark result record

Each benchmark run must record:
- model ID, version, checkpoint SHA-256, and inference configuration;
- dataset ID/version and test split identifier;
- date, hardware/GPU, driver/runtime versions, precision, and batch size;
- exact metric definitions, evaluator versions, sample counts, and exclusions;
- p50/p95 latency, sustained FPS, dropped frames, peak VRAM, and cost calculation;
- known failures, confidence intervals where applicable, and reviewer sign-off.

Never compare two models using different test subjects, different preprocessing, or different metric implementations without clearly marking the comparison as non-equivalent.

## 5. Release gates

A model is not eligible for a paid release until all gates pass:

- **Rights gate:** model weights, code, detectors, pose estimators, training data, and evaluation data each have documented commercial permissions.
- **Consent gate:** required subject permissions and dataset audit are verified.
- **Integrity gate:** immutable checkpoint hash and reproducible model manifest validate.
- **Quality gate:** pre-agreed thresholds pass on the locked test set, including failure-rate limits.
- **Safety gate:** impersonation/consent controls, abuse reporting, and deletion procedures are tested.
- **Operations gate:** latency, uptime, capacity, and cost per generated minute are measured on the intended hardware.
- **Product gate:** recording output and live-call output are separately tested; a recording demo is not evidence of real-time readiness.

Thresholds must be chosen before evaluating candidate models and recorded in a versioned benchmark plan. This document intentionally does not invent numerical pass marks before a baseline model and test set exist.

## 6. Current SPEEDY LIVE status

At the time this specification was added:
- The web prototype captures face blendshapes, body pose, and hand landmarks.
- The backend has request/schema foundations, motion diagnostics, and local model-artifact rights/integrity checks.
- There is no trained photo-animation checkpoint, no inference engine, no production media-upload pipeline, and no WebRTC calling implementation.
- No identity, lip-sync, visual-quality, latency, or GPU-cost benchmark has yet been measured.

The next implementation step is to build a dataset-manifest validator and benchmark-record validator around this standard. Model selection and GPU provisioning should follow only after commercial rights and a suitable evaluation set are established.
