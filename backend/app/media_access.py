"""Purpose-scoped media authorization rules.

This is a pure policy check, not authentication or persistence. Callers must load
consent and revocation records from a trusted server-side store; never trust
client-submitted consent objects as proof of permission.
"""
from app.consent import ConsentPurpose, ConsentRecord, ConsentRevocation


class MediaAccessDenied(PermissionError):
    """Raised when an actor lacks permission to use a media asset."""


def authorize_media_use(
    *,
    actor_user_id: str,
    media_owner_user_id: str,
    media_consent_record_id: str,
    consent: ConsentRecord,
    purpose: ConsentPurpose,
    revocation: ConsentRevocation | None = None,
) -> None:
    """Require ownership, matching consent, requested purpose, and no revocation."""
    if not actor_user_id or actor_user_id != media_owner_user_id:
        raise MediaAccessDenied("The signed-in user does not own this media asset.")

    if consent.owner_user_id != actor_user_id:
        raise MediaAccessDenied("Consent does not belong to the signed-in user.")

    if consent.consent_record_id != media_consent_record_id:
        raise MediaAccessDenied("Media asset is not linked to this consent record.")

    if purpose not in consent.purposes:
        raise MediaAccessDenied("Consent does not cover the requested processing purpose.")

    if revocation is not None:
        if (
            revocation.owner_user_id == actor_user_id
            and revocation.consent_record_id == consent.consent_record_id
        ):
            raise MediaAccessDenied("Consent has been revoked; media processing is blocked.")
