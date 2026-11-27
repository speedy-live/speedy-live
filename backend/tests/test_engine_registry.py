import pytest
from fastapi.testclient import TestClient

from app.engine import AnimationEngine, AnimationEngineUnavailable, EngineRegistry
from app.engine_contract import EngineManifest, EngineQualificationError
from app.main import app

client = TestClient(app)


class LocalStubEngine(AnimationEngine):
    name = "local-test-engine"
    version = "0.1.0"

    async def generate_recording(self, request, source_image, driving_video, output_path):
        return output_path

    async def generate_live_frames(self, source_image, motion):
        if False:
            yield b""


def manifest(**overrides):
    values = {
        "engine_id": "local-test-engine", "version": "0.1.0",
        "supported_modes": ["full_body"], "supports_streaming": False,
        "checkpoint_sha256": "a" * 64, "code_license": "Apache-2.0",
        "weights_license": "Apache-2.0", "dependency_review_id": "deps-001",
        "dataset_rights_review_id": "dataset-001", "commercial_rights_verified": True,
        "inference_entrypoint": "local_worker.infer:run",
    }
    values.update(overrides)
    return EngineManifest(**values)


def test_empty_registry_fails_closed():
    registry = EngineRegistry()
    assert registry.status()["configured"] is False
    with pytest.raises(AnimationEngineUnavailable):
        registry.get("full_body")


def test_registry_rejects_identity_mismatch():
    with pytest.raises(EngineQualificationError, match="identity/version"):
        EngineRegistry().register(LocalStubEngine(), manifest(engine_id="other"))


def test_registry_accepts_matching_qualified_adapter():
    registry = EngineRegistry()
    engine = LocalStubEngine()
    registry.register(engine, manifest())
    assert registry.get("full_body") is engine
    assert registry.status()["engine_id"] == engine.name


def test_registry_rejects_portrait_when_not_supported():
    registry = EngineRegistry()
    registry.register(LocalStubEngine(), manifest())
    with pytest.raises(EngineQualificationError, match="does not support portrait"):
        registry.get("portrait", live=True)


def test_registry_rejects_missing_commercial_rights():
    with pytest.raises(EngineQualificationError, match="commercial-rights"):
        EngineRegistry().register(LocalStubEngine(), manifest(commercial_rights_verified=False))


def test_api_reports_engine_unconfigured():
    assert client.get("/engine/status").json()["configured"] is False
    assert client.get("/ready").json()["status"] == "not_ready"


def test_api_rejects_unknown_mode():
    assert client.get("/engine/capabilities/unknown").status_code == 422


def test_api_returns_503_without_registered_engine():
    response = client.get("/engine/capabilities/full_body")
    assert response.status_code == 503
