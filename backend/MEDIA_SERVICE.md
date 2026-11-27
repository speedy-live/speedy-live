# Private media service orchestration

`app/media_service.py` combines the local private image store with persistent media ownership and consent metadata. Upload writes validated bytes first, registers metadata second, and attempts compensating file deletion if metadata registration fails. Retrieval checks the persistent owner, purpose and revocation policy before reading the private file.

This service is internal only. It has no HTTP routes and does not authenticate callers. Its `actor_user_id` must be obtained from a verified server-side session, never from a browser-supplied owner ID. A failure during compensating deletion requires operator reconciliation; production needs a durable cleanup/outbox process, audit logging, rate limits, quotas, malware scanning, encryption and retention enforcement before customer upload is enabled.
