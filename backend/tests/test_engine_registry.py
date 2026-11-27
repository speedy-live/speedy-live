import asyncio
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from app.engine import AnimationEngine, AnimationEngineUnavailable, EngineRegistry
from app.engine_contract import EngineManifest, EngineQualificationError
from app.main import app

client = TestClient(app)


class LocalStubEngine(AnimationEngine):
    name = "local-test-engine"
    version = "0.1.0"

    async def health_check(self):
        return True

    async def generate_recording(self, request, source_image, driving_video, output_path):
        return output_path

    async def generate_live_frames(self, source_image, motion):
        if False:
            yield b""


def manifest(**overrides):
    values = {
        "engine_id": "local-test-engine", "version": "0.1.0",
        "supported_modes": ["full_body"], "supports_streaming": False,
        "checkpoint_sha256": None, "code_license": "Apache-2.0",
        "weights_license": "Apache-2.0", "dependency_review_id": "deps-001",
        "dataset_rights_review_id": "dataset-001", "commercial_rights_verified": True,
        "inference_entrypoint": "local_worker.infer:run",
    }
    values.update(overrides)
    return EngineManifest(**values)


def artifact_manifest(tmp_path, *, commercial=True, consent=True):
    checkpoint = tmp_path / "weights.bin"
    checkpoint.write_bytes(b"synthetic-test-checkpoint")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    data = {
        "model_id": "local-test-engine", "version": "0.1.0",
        "task": "full_body_animation", "checkpoint_file": "weights.bin",
        "checkpoint_sha256": digest, "architecture": "synthetic-test-only",
        "input_contract": "speedy_motion_v1", "output_contract": "rgb_frames_v1",
        "commercial_use_allowed": commercial, "training_data_consent_verified": consent,
    }
    path = tmp_path / "model-manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path, digest


def test_empty_registry_fails_closed():
    registry = EngineRegistry()
    assert registry.status()["configured"] is False
    assert registry.status()["operational"] is False
    with pytest.raises(AnimationEngineUnavailable):
        registry.get("full_body")


def test_registry_rejects_identity_mismatch(tmp_path):
    path, digest = artifact_manifest(tmp_path)
    with pytest.raises(EngineQualificationError, match="identity/version"):
        EngineRegistry().register(LocalStubEngine(), manifest(engine_id="other", checkpoint_sha256=digest), path)


def test_registry_accepts_only_matching_verified_local_artifact(tmp_path):
    path, digest = artifact_manifest(tmp_path)
    registry = EngineRegistry()
    engine = LocalStubEngine()
    registry.register(engine, manifest(checkpoint_sha256=digest), path)
    assert registry.status()["configured"] is True
    assert registry.status()["operational"] is False
    assert asyncio.run(registry.check_runtime()) is True
    assert registry.get("full_body") is engine
    assert registry.status()["engine_id"] == engine.name
    assert registry.status()["operational"] is True


def test_registry_rejects_checkpoint_hash_mismatch(tmp_path):
    path, _ = artifact_manifest(tmp_path)
    with pytest.raises(EngineQualificationError, match="checkpoint hash"):
        EngineRegistry().register(LocalStubEngine(), manifest(checkpoint_sha256="a" * 64), path)


def test_registry_rejects_missing_commercial_rights(tmp_path):
    path, digest = artifact_manifest(tmp_path, commercial=False)
    with pytest.raises(EngineQualificationError, match="commercial"):
        EngineRegistry().register(LocalStubEngine(), manifest(checkpoint_sha256=digest), path)


def test_registry_rejects_unverified_training_consent(tmp_path):
    path, digest = artifact_manifest(tmp_path, consent=False)
    with pytest.raises(EngineQualificationError, match="consent"):
        EngineRegistry().register(LocalStubEngine(), manifest(checkpoint_sha256=digest), path)


def test_registry_rejects_portrait_when_artifact_is_full_body(tmp_path):
    path, digest = artifact_manifest(tmp_path)
    registry = EngineRegistry()
    registry.register(LocalStubEngine(), manifest(checkpoint_sha256=digest), path)
    assert asyncio.run(registry.check_runtime()) is True
    with pytest.raises(EngineQualificationError, match="does not support portrait"):
        registry.get("portrait", live=True)


def test_runtime_health_failure_keeps_engine_unavailable(tmp_path):
    class BrokenRuntimeEngine(LocalStubEngine):
        async def health_check(self):
            raise RuntimeError("model initialization failed")

    path, digest = artifact_manifest(tmp_path)
    registry = EngineRegistry()
    registry.register(BrokenRuntimeEngine(), manifest(checkpoint_sha256=digest), path)
    assert asyncio.run(registry.check_runtime()) is False
    assert registry.status()["configured"] is True
    assert registry.status()["operational"] is False
    with pytest.raises(AnimationEngineUnavailable, match="runtime health"):
        registry.get("full_body")


def test_api_reports_engine_unconfigured():
    assert client.get("/engine/status").json()["configured"] is False
    assert client.get("/ready").json()["status"] == "not_ready"
    assert client.get("/ready").json()["customer_animation_enabled"] is False


def test_api_rejects_unknown_mode():
    assert client.get("/engine/capabilities/unknown").status_code == 422


def test_api_returns_503_without_registered_engine():
    response = client.get("/engine/capabilities/full_body")
    assert response.status_code == 503
