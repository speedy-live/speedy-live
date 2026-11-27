import hashlib
import json

import pytest

from app.engine import AnimationEngine, EngineRegistry
from app.engine_contract import EngineManifest, EngineQualificationError
from app.engine_loader import load_local_engine


class LocalAdapterEngine(AnimationEngine):
    name = "loader-test-engine"
    version = "1.0"

    async def generate_recording(self, request, source_image, driving_video, output_path):
        return output_path

    async def generate_live_frames(self, source_image, motion):
        if False:
            yield b""


def setup_local_files(tmp_path, *, factory_body=None):
    root = tmp_path / "local_engines"
    root.mkdir()
    checkpoint = root / "weights.bin"
    checkpoint.write_bytes(b"loader-test-weights")
    digest = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    artifact = root / "model-manifest.json"
    artifact.write_text(json.dumps({
        "model_id": "loader-test-engine", "version": "1.0",
        "task": "full_body_animation", "checkpoint_file": "weights.bin",
        "checkpoint_sha256": digest, "architecture": "test-only",
        "input_contract": "speedy_motion_v1", "output_contract": "rgb_frames_v1",
        "commercial_use_allowed": True, "training_data_consent_verified": True,
    }), encoding="utf-8")
    adapter = root / "adapter.py"
    adapter.write_text(factory_body or (
        "from app.engine import AnimationEngine\n"
        "from app.engine_contract import EngineManifest\n"
        "class TestEngine(AnimationEngine):\n"
        " name='loader-test-engine'\n"
        " version='1.0'\n"
        " async def generate_recording(self, request, source_image, driving_video, output_path): return output_path\n"
        " async def generate_live_frames(self, source_image, motion):\n"
        "  if False: yield b''\n"
        "def create_engine():\n"
        " return TestEngine(), EngineManifest(**" + repr({
            "engine_id": "loader-test-engine", "version": "1.0",
            "supported_modes": ["full_body"], "supports_streaming": False,
            "checkpoint_sha256": digest, "code_license": "MIT", "weights_license": "MIT",
            "dependency_review_id": "deps-test", "dataset_rights_review_id": "data-test",
            "commercial_rights_verified": True, "inference_entrypoint": "adapter:create_engine",
        }) + ")\n"
    ), encoding="utf-8")
    return root, adapter, artifact


def test_loader_registers_verified_local_adapter(tmp_path):
    root, adapter, artifact = setup_local_files(tmp_path)
    registry = EngineRegistry()
    load_local_engine(registry, adapter, artifact, allowed_root=root)
    assert registry.status()["configured"] is True
    assert registry.status()["runtime_healthy"] is False
    assert registry.status()["operational"] is False


def test_loader_rejects_adapter_outside_owned_directory(tmp_path):
    root, adapter, artifact = setup_local_files(tmp_path)
    outside = tmp_path / "outside.py"
    outside.write_text(adapter.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(EngineQualificationError, match="inside backend/local_engines"):
        load_local_engine(EngineRegistry(), outside, artifact, allowed_root=root)


def test_loader_rejects_adapter_without_factory(tmp_path):
    root, adapter, artifact = setup_local_files(tmp_path, factory_body="value = 1\n")
    with pytest.raises(EngineQualificationError, match="create_engine"):
        load_local_engine(EngineRegistry(), adapter, artifact, allowed_root=root)


def test_loader_rejects_invalid_factory_result(tmp_path):
    root, adapter, artifact = setup_local_files(tmp_path, factory_body="def create_engine(): return None\n")
    with pytest.raises(EngineQualificationError, match="invalid engine"):
        load_local_engine(EngineRegistry(), adapter, artifact, allowed_root=root)


def test_loader_wraps_adapter_import_failure(tmp_path):
    root, adapter, artifact = setup_local_files(tmp_path, factory_body="raise RuntimeError('broken import')\n")
    with pytest.raises(EngineQualificationError, match="import or factory failed"):
        load_local_engine(EngineRegistry(), adapter, artifact, allowed_root=root)
