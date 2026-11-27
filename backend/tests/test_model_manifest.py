import hashlib
import json
from pathlib import Path

import pytest

from app.model_manifest import ModelArtifactError, verify_model_artifact


def write_artifact(tmp_path, *, commercial=True, consent=True, checkpoint_file="weights.bin"):
    checkpoint = tmp_path / checkpoint_file
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    checkpoint.write_bytes(b"speedy-live-test-checkpoint")
    manifest = {
        "model_id": "speedy-portrait-alpha",
        "version": "0.1.0",
        "task": "portrait_animation",
        "checkpoint_file": checkpoint_file,
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "architecture": "SPEEDY-LIVE-owned-model",
        "input_contract": "speedy_motion_v1",
        "output_contract": "rgb_frames_v1",
        "commercial_use_allowed": commercial,
        "training_data_consent_verified": consent,
    }
    path = tmp_path / "model-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return path, checkpoint


def test_verifies_local_model_artifact_and_rights(tmp_path):
    path, _ = write_artifact(tmp_path)
    result = verify_model_artifact(path)
    assert result.model_id == "speedy-portrait-alpha"
    assert result.task == "portrait_animation"


def test_rejects_research_only_model(tmp_path):
    path, _ = write_artifact(tmp_path, commercial=False)
    with pytest.raises(ModelArtifactError, match="commercial"):
        verify_model_artifact(path)


def test_rejects_unverified_training_consent(tmp_path):
    path, _ = write_artifact(tmp_path, consent=False)
    with pytest.raises(ModelArtifactError, match="consent"):
        verify_model_artifact(path)


def test_rejects_checkpoint_hash_mismatch(tmp_path):
    path, checkpoint = write_artifact(tmp_path)
    checkpoint.write_bytes(b"changed")
    with pytest.raises(ModelArtifactError, match="SHA-256"):
        verify_model_artifact(path)


def test_rejects_missing_checkpoint(tmp_path):
    path, checkpoint = write_artifact(tmp_path)
    checkpoint.unlink()
    with pytest.raises(ModelArtifactError, match="missing"):
        verify_model_artifact(path)


def test_accepts_checkpoint_in_nested_model_directory(tmp_path):
    path, checkpoint = write_artifact(tmp_path, checkpoint_file="weights/model.bin")
    result = verify_model_artifact(path)
    assert result.model_id == "speedy-portrait-alpha"
    assert checkpoint.is_file()


def test_rejects_checkpoint_path_traversal(tmp_path):
    outside = tmp_path.parent / "outside-model.bin"
    outside.write_bytes(b"outside")
    manifest_path = tmp_path / "model-manifest.json"
    manifest_path.write_text(
        json.dumps({
            "model_id": "speedy-portrait-alpha",
            "version": "0.1.0",
            "task": "portrait_animation",
            "checkpoint_file": "../outside-model.bin",
            "checkpoint_sha256": hashlib.sha256(b"outside").hexdigest(),
            "architecture": "SPEEDY-LIVE-owned-model",
            "input_contract": "speedy_motion_v1",
            "output_contract": "rgb_frames_v1",
            "commercial_use_allowed": True,
            "training_data_consent_verified": True,
        }),
        encoding="utf-8",
    )
    with pytest.raises(ModelArtifactError, match="beside or below"):
        verify_model_artifact(manifest_path)


def test_hashes_large_checkpoint_incrementally(tmp_path, monkeypatch):
    path, checkpoint = write_artifact(tmp_path)
    checkpoint.write_bytes(b"x" * (9 * 1024 * 1024))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["checkpoint_sha256"] = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    path.write_text(json.dumps(manifest), encoding="utf-8")

    def forbidden_read_bytes(_self):
        raise AssertionError("Checkpoint must not be loaded all at once.")

    monkeypatch.setattr(Path, "read_bytes", forbidden_read_bytes)
    result = verify_model_artifact(path)
    assert result.model_id == "speedy-portrait-alpha"
