# API authentication and role separation

The API verifies short-lived HS256 bearer tokens. A trusted authentication service must
issue them; this API intentionally has no public token-minting or role-changing endpoint.

Required claims: `sub` (immutable user ID), `role` (`customer` or `admin`),
`iss`, `aud`, `iat`, and `exp`. Tokens are limited to one hour. The API checks
the signature, issuer, audience, role, issue time and expiry on every protected request.

Server environment variables:
- `AUTH_SIGNING_KEY`: secret of at least 32 characters, stored only on the backend.
- `AUTH_TOKEN_ISSUER`: trusted issuer identifier (default `speedy-live-auth`).
- `AUTH_TOKEN_AUDIENCE`: this API's audience (default `speedy-live-api`).

Never place the signing key in Vite/browser variables, Git, customer responses, or logs.
Never accept a role or user ID from a request body as authentication. Admin tokens must
be issued only after a trusted admin authentication process with MFA and server-side
role assignment. Customer accounts cannot promote themselves.

Route classification:
- `/health`, `/ready`: operational status only.
- `/customer/*`: CUSTOMER ONLY; requires a customer principal.
- `/admin/*`: ADMIN ONLY; requires an admin principal.
- `/engine/status`: ADMIN ONLY.
- `/engine/capabilities/{mode}`: CUSTOMER ONLY and additionally gated by model release approval.
- `/motion/diagnostics`: SHARED BACKEND SERVICE; accepts motion diagnostics only and does not expose customer records.

This is the authorization foundation, not a complete login/session product. Token
issuance, password/email verification, refresh-token rotation, revocation/session storage,
MFA enrollment, admin account provisioning, CSRF protections for cookie sessions, and
frontend login/dashboard routing remain separate work before production launch.
