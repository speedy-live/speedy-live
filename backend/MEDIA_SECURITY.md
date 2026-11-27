# Media and consent security boundary

## Current implementation boundary

SPEEDY LIVE does not currently accept, persist, or process customer photographs or recordings. The browser Photo Studio uses a temporary local object URL. Do not treat a UI checkbox, client-provided media ID, or this schema as proof of consent.

## Consent contract

`app/consent.py` defines the server-side data shape expected for explicit consent:
- the authenticated account that owns the request;
- confirmation that the uploader has rights to use the image;
- confirmation that the depicted person has given permission;
- specific purposes (photo animation, live calling, recording);
- policy version and timezone-aware timestamp;
- a revocation record shape.

These Pydantic contracts validate data only. They do not authenticate the user, prove the person gave consent, store the record, revoke existing jobs, or delete media. A future authenticated service must persist consent and revocation events in durable storage and check active consent immediately before every processing job and live session.

## Required upload implementation before launch

1. Authenticate the customer and authorize access to the target account.
2. Require an active consent record covering the exact requested purpose. Do not infer consent for recording or live calling from photo-animation consent.
3. Accept only JPEG, PNG, or WebP after inspecting file signatures and decoding the actual image. Do not trust the browser MIME type or filename.
4. Enforce request-body and decoded-pixel limits, reject malformed/animated formats unless explicitly supported, strip metadata where appropriate, and re-encode safe image derivatives.
5. Store originals privately under random server-generated IDs; never expose bucket paths or public object URLs.
6. Use short-lived, purpose-scoped signed access and prevent cross-account media access.
7. Record access and processing events without logging image bytes or sensitive URLs.
8. Provide authenticated deletion and retention expiry. Deletion must cover originals, derivatives, caches, generated outputs, and queued/running jobs.
9. Rate-limit uploads and processing, scan for abuse, and apply an incident response process.
10. Test authorization, MIME spoofing, decompression/pixel bombs, path traversal, cross-user access, expired URLs, revocation races, and deletion.

## Revocation semantics

Revocation must stop new processing immediately. The service must cancel queued work and prevent future live sessions or recordings using that consent. The product must explain what happens to outputs already downloaded or shared; deletion from SPEEDY LIVE storage cannot retrieve copies outside our control.

## No public upload endpoint yet

Do not add an unauthenticated upload route or accept media IDs supplied by the browser as authorization. The current backend has no customer authentication, object storage, durable consent repository, or deletion worker, so upload endpoints remain intentionally disabled.
