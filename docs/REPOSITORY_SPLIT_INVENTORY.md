# SPEEDY LIVE — Repository Split Inventory

This inventory is committed on the development branch `ai-backend-foundation` only. It does not change `main` or production.

## Target repository ownership

| Target | Contents | Current state |
|---|---|---|
| `speedy-live-website` | Customer-only React/Vite frontend | Repository created; scope documented on `staging-organization`; customer application not yet migrated |
| `speedy-live-admin` | Separate operator/admin frontend | Repository created; scope documented on `staging-organization`; no finished admin app exists in source |
| `speedy-live-api` | FastAPI backend, auth, media, engine contracts, tests | Repository created; scope documented on `staging-organization`; source not copied because target is public |
| `speedy-live` | Original preserved source and development history | Keep as source of truth until migration is verified |

## Existing source inventory

### Backend — intended for `speedy-live-api`
- `backend/app/main.py`: FastAPI routes and application setup.
- `backend/app/account_store.py`, `auth.py`, `config.py`, `email_delivery.py`: account/authentication and verification foundations.
- `backend/app/consent.py`, `media_access.py`, `media_repository.py`, `media_service.py`, `media_storage.py`, `media_validation.py`: consent and private-media service foundation.
- `backend/app/engine.py`, `engine_contract.py`, `engine_loader.py`, `model_manifest.py`, `benchmark_manifest.py`, `dataset_manifest.py`: engine contracts, qualification and model-loading foundation.
- `backend/app/job_lifecycle.py`, `motion_processing.py`, `schemas.py`, `audio_contract.py`: processing contracts and diagnostics.
- `backend/tests/`: automated tests for auth, API, engine, consent, media, motion and schemas.
- `backend/*.md`: deployment, authorization, media and service notes.

### Existing browser prototype — source components requiring product review
- `src/App.tsx`: prototype shell and browser motion-tracking workflow.
- `src/PhotoStudio.tsx` and `src/photo-studio.css`: local-only photo preview and image framing checks; no AI animation or upload.
- `src/MotionCapture.tsx` and `src/motion-capture.css`: research movement capture/diagnostics; not customer animation.
- `src/AvatarPreview.tsx` and `src/avatar-preview.css`: experimental 3D landmark visualisation.
- `src/BackendConnection.tsx` and `src/backend-connection.css`: backend readiness panel; internal status information, not suitable for the public customer UI as-is.
- `src/EngineWorkbench.tsx` and `src/engine-workbench.css`: internal engine qualification/roadmap panel; belongs in a protected operator experience, not the customer site.
- `src/main.tsx`, `src/styles.css`, `index.html`, `package.json`, `tsconfig.json`, `vite.config.ts`: Vite app foundation and build configuration.

## Admin application gap
There is no complete admin frontend in the inspected source tree. The Engine Workbench and backend status panel are research/diagnostic components only. A real protected admin dashboard must be built separately; do not relabel those panels as a finished admin product.

## Migration safety rules
1. Keep `main` and production untouched.
2. Do not copy backend source to a public repository. All four repositories were verified public at the time this inventory was written.
3. Make the API and admin repositories private, then verify visibility before moving backend/admin implementation.
4. Keep customer UI free of engine internals, admin data, secret values and privileged controls.
5. The backend must enforce roles and ownership on every protected endpoint.
6. Do not migrate secrets, local databases, customer media, model weights, or generated artifacts.
7. Migrate by reviewed file groups, then run tests/builds before any Cloudflare connection.
8. No staging or production deployments have been changed by this inventory commit.

## Unfinished product capabilities
No qualified animation model is installed. Real photo animation, full-body inference, live calling, recording, and a complete admin dashboard are not yet implemented. Existing photo preview and motion diagnostics must not be described as those finished features.
