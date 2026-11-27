# SPEEDY LIVE internal motion research harness

## Purpose

This milestone establishes the data contracts and engine boundary for our own future animation system. It does not generate video, upload media, store customer photographs, or expose an inference API.

## Contracts

- `Landmark`: normalized image coordinates and optional visibility.
- `FaceControls`: estimated head rotation and facial blendshape scores.
- `MotionFrame`: timestamped, sequenced body/hand/face controls.
- `GenerationRequest`: internal reference IDs plus explicit consent record ID.
- `GenerationStatus`: stable job state and progress shape.

The IDs are references only. No endpoint currently resolves them to media.

## Engine boundary

`backend/app/engine.py` defines two future execution modes:
- asynchronous recording generation from a source image and driving video;
- asynchronous live frame generation from a stream of motion frames.

The default implementation deliberately raises `AnimationEngineUnavailable`. This prevents a false success response before a real model exists.

## Next experiment

1. Build a local capture exporter that saves timestamped pose, hand and face controls from the existing browser tracker.
2. Keep media and control data local during the first experiment; do not upload customer images.
3. Create a small consented internal test set using images/videos the contributors explicitly permit for research.
4. Measure landmark stability, missing-point frequency, timestamp drift and motion smoothness.
5. Define training examples and evaluation splits before model training.
6. Only then implement a first owned motion-conditioning model and compare its output against the baseline.

## Test command

From `backend/`:

```bash
pip install -e ".[dev]"
pytest
```

Passing schema tests validates data contracts only. It does not validate AI quality or animation capability.
