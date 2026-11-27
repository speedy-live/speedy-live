import pytest
from pydantic import ValidationError

from app.engine_contract import (
    EngineManifest,
    EngineQualificationError,
    require_engine_eligibility,
)


HASH = "a" * 64


def manifest(**overrides) -> EngineManifest:
    values = {
        "engine_id": "local-test-engine",
        "version": "0.1.0",
        "supported_modes": ["full_body"],
        "supports_streaming": False,
        "checkpoint_sha256": HASH,
        "code_license": "Apache-2.0",
        "weights_license": "Apache-2.0",
        "dependency_review_id": "deps-review-001",
        "dataset_rights_review_id": "dataset-review-001",
        "commercial_rights_verified": True,
        "inference_entrypoint": "worker.infer:run",
        "minimum_gpu_memory_gb": 48,
        "tested_gpu": "test GPU",
    }
    values.update(overrides)
    return EngineManifest(**values)


def test_manifest_rejects_malformed_checkpoint_hash() -> None:
    with pytest.raises(ValidationError):
        manifest(checkpoint_sha256="not-a-sha")


def test_complete_manifest_is_eligible_for_private_test() -> None:
    candidate = manifest()
    assert candidate.has_runnable_artifact
    assert candidate.rights_review_complete
    assert candidate.eligible_for_private_test


def test_manifest_without_rights_evidence_is_not_eligible() -> None:
    candidate = manifest(commercial_rights_verified=False)
    assert not candidate.rights_review_complete
    assert not candidate.eligible_for_private_test


def test_full_body_candidate_cannot_be_used_as_portrait_live_engine() -> None:
    candidate = manifest()
    with pytest.raises(EngineQualificationError, match="does not support portrait"):
        require_engine_eligibility(candidate, "portrait")


def test_live_portrait_requires_streaming_capability() -> None:
    candidate = manifest(supported_modes=["portrait"], supports_streaming=False)
    with pytest.raises(EngineQualificationError, match="cannot be used for live"):
        require_engine_eligibility(candidate, "portrait")


def test_missing_inference_artifact_fails_closed() -> None:
    candidate = manifest(checkpoint_sha256=None, inference_entrypoint=None)
    with pytest.raises(EngineQualificationError, match="no verified checkpoint"):
        require_engine_eligibility(candidate, "full_body")


def test_rights_gate_can_only_be_bypassed_for_noncommercial_lab_test() -> None:
    candidate = manifest(commercial_rights_verified=False)
    with pytest.raises(EngineQualificationError, match="commercial-rights"):
        require_engine_eligibility(candidate, "full_body")
    require_engine_eligibility(candidate, "full_body", require_commercial_rights=False)
