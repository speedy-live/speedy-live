# SPEEDY LIVE — Source Reconciliation

Checked 27 November 2026 against the GitHub trees of the original repository.

## Verified facts

- The original repository's `main` branch contains a small React/Vite browser prototype: `src/App.tsx`, `src/PhotoStudio.tsx`, `src/AvatarPreview.tsx`, CSS, and Vite configuration.
- The original repository's `ai-backend-foundation` branch currently contains research/architecture Markdown documents and this repository inventory. Its current Git tree does **not** contain a `backend/` directory, a `src/` directory, or the FastAPI/auth/media implementation previously described in the inventory.
- The new `speedy-live-website`, `speedy-live-admin`, and `speedy-live-api` repositories currently contain setup README files only on their checked staging branches.
- The website repository also has a `staging-website-import` branch, but its checked tree contains only a README.

## Migration decision

Do not claim that the backend implementation has been migrated. Do not copy the prototype into the customer website as if it were a finished customer product: it is a movement-tracking research prototype and exposes diagnostic controls that do not belong in the customer experience.

Before a safe code migration can continue, locate the actual backend source revision or supply its correct repository/branch. Once located, review it for secrets and customer data before copying selected source files into the API staging branch.

## Production and security

- Keep all work on staging/development branches.
- Do not change the original `main` branch.
- Do not deploy production.
- Public repository visibility is intentional per the owner. Never commit secrets, credentials, private customer data, photographs, or model weights.
- The separate admin application still needs to be built; no completed admin frontend was found in the inspected source tree.
