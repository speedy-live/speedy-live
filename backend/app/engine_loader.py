"""Safe startup loader for locally installed SPEEDY LIVE engine adapters.

Adapters are Python files placed inside backend/local_engines. Nothing is
downloaded, and incomplete or invalid configuration leaves the service unready.
"""
import importlib.util
import logging
from pathlib import Path

from app.engine import AnimationEngine, EngineRegistry
from app.engine_contract import EngineManifest, EngineQualificationError

logger = logging.getLogger(__name__)


def load_local_engine(
    registry: EngineRegistry,
    adapter_path: Path,
    artifact_manifest_path: Path,
    *,
    allowed_root: Path,
) -> None:
    root = allowed_root.resolve()
    adapter = adapter_path.resolve()
    artifact = artifact_manifest_path.resolve()
    if root not in adapter.parents or root not in artifact.parents:
        raise EngineQualificationError("Engine adapter and model manifest must be inside backend/local_engines.")
    if not adapter.is_file():
        raise EngineQualificationError("Configured local engine adapter file does not exist.")
    if not artifact.is_file():
        raise EngineQualificationError("Configured local model artifact manifest does not exist.")

    try:
        spec = importlib.util.spec_from_file_location("speedy_live_local_engine_adapter", adapter)
        if spec is None or spec.loader is None:
            raise EngineQualificationError("Could not load the configured local engine adapter.")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        factory = getattr(module, "create_engine", None)
        if not callable(factory):
            raise EngineQualificationError("Local engine adapter must define create_engine().")
        created = factory()
    except EngineQualificationError:
        raise
    except Exception as exc:
        raise EngineQualificationError(
            f"Local engine adapter import or factory failed: {type(exc).__name__}: {exc}"
        ) from exc

    if not isinstance(created, tuple) or len(created) != 2:
        raise EngineQualificationError(
            "Local engine adapter returned an invalid engine factory result; "
            "create_engine() must return (engine, EngineManifest)."
        )
    engine, manifest = created
    if not isinstance(engine, AnimationEngine) or not isinstance(manifest, EngineManifest):
        raise EngineQualificationError("Adapter factory returned invalid engine or manifest types.")

    registry.register(engine, manifest, artifact)
    logger.info("Registered verified local SPEEDY LIVE engine: %s", engine.name)
