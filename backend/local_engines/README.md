# Local engine installation directory

This directory is reserved for SPEEDY LIVE engine adapter code and model manifests.
It is intentionally not populated with a fake or placeholder model.

To enable an adapter in a private environment:

1. Place the adapter Python file and its model manifest/checkpoint under this directory.
2. The adapter must expose `create_engine()`, returning an `AnimationEngine` instance and an `EngineManifest`.
3. Ensure the manifest's engine ID, version, supported task and checkpoint SHA-256 exactly match the model artifact manifest.
4. Complete and independently document commercial rights, dependency review and dataset rights review.
5. Set:
   - `ANIMATION_ENGINE` to a non-`unconfigured` label.
   - `ANIMATION_ENGINE_ADAPTER_PATH` to the adapter's path.
   - `ANIMATION_MODEL_MANIFEST_PATH` to the model manifest's path.
6. Restart the backend and check `/engine/status` and `/ready`.

The loader only imports files contained in this directory. It does not download weights,
contact hosted inference services, or make an unqualified model ready. Registration
is not proof of runtime quality: real inference, model health, performance and safety
must still pass separate qualification tests before customer use.

Never commit private customer photos, secrets, production credentials or large model
weights to Git. Keep private checkpoints on secured model storage mounted by the
self-operated inference host.
