import json

import pytest

from app.benchmark_manifest import BenchmarkRecordError, validate_benchmark_record_json
from app.dataset_manifest import DatasetManifestError, validate_dataset_manifest_json


def sample_asset(**overrides):
    asset = {
        "asset_id": "asset_001",
        "subject_id": "subject_001",
        "source_type": "video",
        "source_reference": "private://dataset/asset_001",
        "consent_record_id": "consent_001",
        "permitted_purposes": ["training", "commercial_generation"],
        "commercial_use_allowed": True,
        "sha256": "a" * 64,
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "duration_ms": 12000,
        "audio_present": True,
        "face_visible": True,
        "body_visibility": "full",
        "left_hand_visible": True,
        "right_hand_visible": True,
    }
    asset.update(overrides)
    return asset


def sample_dataset(**overrides):
    data = {
        "dataset_id": "speedy-motion-v1",
        "version": "0.1.0",
        "purpose": "training",
        "commercial_use_allowed": True,
        "consent_audit_verified": True,
        "assets": [sample_asset()],
    }
    data.update(overrides)
    return data


def test_accepts_valid_commercial_dataset_declaration():
    result = validate_dataset_manifest_json(json.dumps(sample_dataset()))
    assert result.assets[0].subject_id == "subject_001"


def test_rejects_duplicate_asset_ids():
    asset = sample_asset()
    with pytest.raises(DatasetManifestError, match="unique"):
        validate_dataset_manifest_json(json.dumps(sample_dataset(assets=[asset, asset])))


def test_rejects_commercial_dataset_without_consent_audit():
    with pytest.raises(DatasetManifestError, match="consent audit"):
        validate_dataset_manifest_json(json.dumps(sample_dataset(consent_audit_verified=False)))


def test_rejects_asset_without_required_purpose():
    with pytest.raises(DatasetManifestError, match="does not permit"):
        validate_dataset_manifest_json(json.dumps(sample_dataset(
            assets=[sample_asset(permitted_purposes=["validation"])]
        )))


def test_rejects_uncleared_asset_in_commercial_dataset():
    with pytest.raises(DatasetManifestError, match="uncleared"):
        validate_dataset_manifest_json(json.dumps(sample_dataset(
            assets=[sample_asset(commercial_use_allowed=False)]
        )))


def test_rejects_non_private_media_reference():
    with pytest.raises(DatasetManifestError, match="private://"):
        validate_dataset_manifest_json(json.dumps(sample_dataset(
            assets=[sample_asset(source_reference="https://example.com/video.mp4")]
        )))


def sample_benchmark(**overrides):
    data = {
        "benchmark_id": "portrait-baseline-001",
        "model_id": "speedy-portrait",
        "model_version": "0.1.0",
        "checkpoint_sha256": "b" * 64,
        "dataset_id": "speedy-motion-v1",
        "dataset_version": "0.1.0",
        "split": "testing",
        "evaluated_at": "2026-11-27T10:00:00Z",
        "hardware": "NVIDIA GPU - test device",
        "runtime": "PyTorch - benchmark build",
        "sample_count": 25,
        "metrics": {
            "identity_similarity_mean": 0.91,
            "latency_p50_ms": 80,
            "latency_p95_ms": 120,
            "generated_fps": 24,
        },
        "notes": "Synthetic test fixture only; not a measured SPEEDY LIVE result.",
    }
    data.update(overrides)
    return data


def test_accepts_well_formed_benchmark_record():
    result = validate_benchmark_record_json(json.dumps(sample_benchmark()))
    assert result.metrics.latency_p95_ms == 120


def test_rejects_p95_latency_below_p50():
    metrics = {"latency_p50_ms": 150, "latency_p95_ms": 100}
    with pytest.raises(BenchmarkRecordError, match="p95"):
        validate_benchmark_record_json(json.dumps(sample_benchmark(metrics=metrics)))


def test_rejects_invalid_checkpoint_hash():
    with pytest.raises(BenchmarkRecordError, match="Invalid benchmark"):
        validate_benchmark_record_json(json.dumps(sample_benchmark(checkpoint_sha256="bad")))


def test_rejects_empty_benchmark_sample():
    with pytest.raises(BenchmarkRecordError, match="Invalid benchmark"):
        validate_benchmark_record_json(json.dumps(sample_benchmark(sample_count=0)))
