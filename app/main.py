from fastapi import FastAPI, Request, HTTPException, BackgroundTasks, Depends
import json
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.schemas import MessageSchema
from app.tasks.message_tasks import process_incoming_message
from app.services.whatsapp_service import close_shared_client
from app.utils.security import verify_whatsapp_signature
from app.utils.logger import setup_logger

logger = setup_logger()

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FarmConnect app (env=%s)", settings.ENVIRONMENT)
    try:
        yield
    finally:
        logger.info("Shutting down FarmConnect app")
        # on shutdown, close shared clients
        await close_shared_client()


app = FastAPI(lifespan=lifespan)


@app.get("/webhook")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def whatsapp_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    raw_body: bytes = Depends(verify_whatsapp_signature),
):
    # Signature verification is handled by the dependency; parse JSON from body
    try:
        data = json.loads(raw_body)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")
    try:
        change = data.get("entry", [])[0].get("changes", [])[0]
        value = change.get("value", {})

        # Standard message payload (messages array)
        messages = value.get("messages", [])
        if messages:
            msg_data = messages[0]
            phone = msg_data.get("from")
            text = msg_data.get("text", {}).get("body")
            timestamp = msg_data.get("timestamp")

        # Handover / messaging_handovers payload (control_passed metadata)
        elif value.get("control_passed") or value.get("messaging_handovers"):
            # prefer direct control_passed, otherwise look under messaging_handovers
            cp = value.get("control_passed") or value.get("messaging_handovers")
            # metadata field may contain a short text message or structured info
            text = cp.get("metadata") if isinstance(cp, dict) else None
            # sender info may be under `sender` or `recipient` depending on sample
            sender = value.get("sender") or value.get("recipient")
            phone = None
            if isinstance(sender, dict):
                phone = sender.get("phone_number") or sender.get("display_phone_number")
            timestamp = value.get("timestamp")

        else:
            raise HTTPException(
                status_code=400, detail="No messages or handover data found"
            )

        # map nested payload to your MessageSchema
        msg = MessageSchema(phone=phone, text=text, timestamp=timestamp)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    payload = msg.model_dump()
    # If a Celery-style `.delay` is present (kept for compatibility/tests), use it.
    if callable(getattr(process_incoming_message, "delay", None)):
        process_incoming_message.delay(payload)
    else:
        # Run in the background using FastAPI's BackgroundTasks
        background_tasks.add_task(process_incoming_message, payload)

    return JSONResponse({"status": "enqueued"})


# shutdown handled by lifespan context manager


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run(app, host="0.0.0.0", port=8000)

#     #  python -m uvicorn app.main:app --reload
