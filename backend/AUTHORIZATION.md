# SPEEDY LIVE authentication and authorization

## Implemented foundation

- SQLite-backed account records with salted PBKDF2-HMAC-SHA256 password hashes.
- Roles are stored on the server as `customer` or `admin`; the login request has no role field.
- Customer sign-in is allowed only after the customer's email has been verified.
- Admin accounts are trusted, operator-provisioned identities and do not require customer email verification.
- `POST /auth/login` issues a signed, 15-minute HS256 bearer token.
- Protected requests verify token signature, algorithm, issuer, audience, expiry and current account status/role.
- Disabling an account or changing its role invalidates its tokens on the next protected request.
- No public registration, role promotion, email verification, password reset, refresh-token or logout endpoint exists yet.

## Route classification

- `/health`, `/ready`: public operational status only.
- `/auth/login`: public sign-in for previously provisioned and verified accounts.
- `/auth/me`, `/customer/*`, `/engine/capabilities/{mode}`: CUSTOMER ONLY.
- `/admin/auth/me`, `/admin/*`, `/engine/status`: ADMIN ONLY.
- `/motion/diagnostics`: shared stateless diagnostics only; it does not read or return customer records.
- Media repository/storage/service classes: internal only; not exposed as HTTP routes.

## Backend environment

- `AUTH_SIGNING_KEY`: backend-only secret with at least 32 characters; use a random high-entropy secret.
- `AUTH_TOKEN_ISSUER`: trusted issuer identifier.
- `AUTH_TOKEN_AUDIENCE`: API audience.
- `AUTH_DATABASE_PATH`: persistent private SQLite account database path.

Never put secrets in Vite variables, browser code, Git, customer responses or logs. Back up the account database securely and restrict its filesystem permissions. Use persistent encrypted storage in production.

## Before production launch

This is not yet a complete production identity platform. Still required:
1. Customer registration and a complete email verification workflow (single-use expiring tokens, secure token storage, resend/attempt limits and email delivery).
2. Admin bootstrap/provisioning workflow, MFA and recovery controls.
3. Session records, logout/revocation and refresh-token rotation.
4. Login rate limits, abuse protection and password reset controls.
5. Frontend customer/admin login and separate dashboard routing.
6. Secure customer media endpoints deriving owner identity only from the verified principal.
7. CSRF protections if browser cookies are adopted; prefer secure HttpOnly cookies over localStorage for browser sessions.
8. Audit logs for admin actions, security events and account changes.
9. Production secrets, persistent encrypted storage, backup and recovery tests.

Customers cannot create admin accounts through the API. Do not add a public account-creation route that accepts a role.
