# Persistent media metadata repository

`app/media_repository.py` provides SQLite-backed persistence for consent records, consent revocations, and media ownership metadata. It enforces unique IDs, foreign-key relationships, owner matching, purpose-specific authorization, and revocation checks when media metadata is retrieved. Database files and their parent directory are restricted to owner-only permissions.

## Integration and security boundary

This is an internal repository layer, not a customer-facing upload API. It does not authenticate users, create sessions, accept HTTP requests, write image bytes, or guarantee encrypted-at-rest storage. The application must derive `actor_user_id` from a verified authentication session and must never trust an owner ID or consent object supplied by a browser.

The media file and metadata database are separate resources. Upload orchestration must handle failures between writing the image and registering its metadata, with cleanup/compensation and periodic orphan reconciliation. Deletion orchestration must remove the private image and metadata, retry partial failures, and audit the result. Do not expose customer uploads until authentication, request limits, quotas, malware scanning, encryption, retention jobs, and end-to-end deletion are implemented and tested.

SQLite is a single-node persistence foundation for development or a single service instance. Before multi-instance production use, select and qualify a shared transactional database and encrypted private object storage.
