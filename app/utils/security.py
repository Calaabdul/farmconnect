from typing import Optional
import hmac
import hashlib

from fastapi import Request, HTTPException

from app.config import get_settings

settings = get_settings()


async def verify_whatsapp_signature(request: Request) -> bytes:
    """Dependency that validates X-Hub-Signature-256 for incoming WhatsApp webhooks.

    Returns the raw request body bytes for handlers to reuse.
    Raises HTTPException(403) when signature is missing or invalid.
    """
    signature_header: Optional[str] = request.headers.get(
        "X-Hub-Signature-256"
    ) or request.headers.get("x-hub-signature-256")
    if not signature_header:
        raise HTTPException(status_code=403, detail="Missing signature header")

    body = await request.body()

    # header format is "sha256=..."
    if signature_header.startswith("sha256="):
        signature = signature_header.split("=", 1)[1]
    else:
        signature = signature_header

    expected = hmac.new(
        bytes(settings.APP_SECRET or "", "utf-8"), msg=body, digestmod=hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    return body
