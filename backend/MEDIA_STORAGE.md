# Private media storage primitive

`app/media_storage.py` adds a local private-storage primitive. It accepts only bytes that pass the existing JPEG/PNG/WebP validator, generates a random 128-bit media identifier, writes files outside the public web root, and uses restrictive directory/file permissions. It supports private reads and deletion by opaque media ID.

## Important limits

This is not yet a customer upload feature:
- no HTTP upload/download/delete routes are exposed;
- no customer authentication or durable ownership metadata is connected;
- no database maps media IDs to owners, consent records, purpose, retention deadline, or lifecycle state;
- local filesystem persistence is not replicated, encrypted-at-rest configuration is not guaranteed by this code, and deployment volumes must be protected;
- no malware scanning, quota enforcement, backup policy, or deletion worker exists.

Do not deploy customer uploads until the service has a persistent encrypted private volume, authenticated metadata repository, ownership and consent checks on every operation, request-body limits at the reverse proxy and application layer, rate limits, audit logging, retention enforcement, and tested deletion of originals, derivatives, caches, outputs, and queued jobs.

A future cloud/object-storage adapter should implement the same private interface and use a private bucket with server-side encryption, least-privilege credentials, and short-lived signed URLs. Never make this directory public or mount it under the frontend static assets.
