import asyncio
import base64
import hmac
import time
import hashlib
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import auth
from app.engine import AnimationEngine, AnimationEngineUnavailable, EngineRegistry
from app.engine_contract import EngineManifest, EngineQualificationError
from app.main import app

client = TestClient(app)

class _ActiveAccountStore:
    def __init__(self, _path):
        pass
    def identity_is_active(self, *, user_id, role):
        return True


AUTH_KEY = "test-signing-key-that-is-at-least-32-bytes-long"


def api_headers(role="customer"):
    def enc(value):
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode()
    now = int(time.time())
    header = enc(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    claims = enc(json.dumps({
        "sub": "engine-test-user", "role": role, "iss": "speedy-live-auth",
        "aud": "speedy-live-api", "iat": now, "exp": now + 300,
    }).encode())
    signature = hmac.new(AUTH_KEY.encode(), f"{header}.{claims}".encode(), "sha256").digest()
    token = f"{header}.{claims}.{enc(signature)}"
    return {"Authorization": f"Bearer {token}"}


def configure_api_auth(monkeypatch):
    monkeypatch.setattr(auth, "AccountStore", _ActiveAccountStore)
    monkeypatch.setattr(auth, "get_settings", lambda: SimpleNamespace(
        auth_signing_key=AUTH_KEY,
        auth_token_issuer="speedy-live-auth",
        auth_token_audience="speedy-live-api",
        auth_database_path="unused-test-db",
    ))



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


def artifact_manifest(tmp_path, *, commercial=True, consent=True, task="full_body_animation"):
    checkpoint = tmp_path / "weights.bin"
    checkpoint.write_bytes(b"synthetic-test-checkpoint")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    data = {
        "model_id": "local-test-engine", "version": "0.1.0",
        "task": task, "checkpoint_file": "weights.bin",
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


def test_api_reports_engine_unconfigured(monkeypatch):
    configure_api_auth(monkeypatch)
    assert client.get("/engine/status").status_code == 401
    assert client.get("/engine/status", headers=api_headers("admin")).json()["configured"] is False
    assert client.get("/ready").json()["status"] == "not_ready"
    assert client.get("/ready").json()["customer_animation_enabled"] is False


def test_api_rejects_unknown_mode(monkeypatch):
    configure_api_auth(monkeypatch)
    assert client.get("/engine/capabilities/unknown", headers=api_headers()).status_code == 422


def test_api_returns_503_without_registered_engine(monkeypatch):
    configure_api_auth(monkeypatch)
    response = client.get("/engine/capabilities/full_body", headers=api_headers())
    assert response.status_code == 503



def test_registry_requires_explicit_audio_driven_portrait_capability(tmp_path):
    path, digest = artifact_manifest(tmp_path, task="portrait_animation")
    registry = EngineRegistry()
    registry.register(
        LocalStubEngine(),
        manifest(
            supported_modes=["portrait"],
            supports_streaming=True,
            checkpoint_sha256=digest,
            supports_audio_driven_portrait=False,
        ),
        path,
    )
    assert asyncio.run(registry.check_runtime()) is True
    with pytest.raises(AnimationEngineUnavailable, match="audio-driven portrait capability"):
        registry.get("portrait", live=True, audio_driven=True)


def test_registry_allows_audio_driven_portrait_only_when_declared(tmp_path):
    path, digest = artifact_manifest(tmp_path, task="portrait_animation")
    registry = EngineRegistry()
    engine = LocalStubEngine()
    registry.register(
        engine,
        manifest(
            supported_modes=["portrait"],
            supports_streaming=True,
            checkpoint_sha256=digest,
            supports_audio_driven_portrait=True,
        ),
        path,
    )
    assert asyncio.run(registry.check_runtime()) is True
    assert registry.get("portrait", live=True, audio_driven=True) is engine


def test_audio_driven_generation_cannot_be_requested_for_full_body(tmp_path):
    path, digest = artifact_manifest(tmp_path)
    registry = EngineRegistry()
    registry.register(LocalStubEngine(), manifest(checkpoint_sha256=digest), path)
    assert asyncio.run(registry.check_runtime()) is True
    with pytest.raises(AnimationEngineUnavailable, match="only for portrait"):
        registry.get("full_body", audio_driven=True)
