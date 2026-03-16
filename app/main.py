from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.models.schemas import MessageSchema
from app.tasks.message_tasks import process_incoming_message

settings = get_settings()

app = FastAPI()


@app.get("/webhooks")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    # simple API key check for security
    key = request.headers.get("x-api-key")
    if key != settings.WHATSAPP_VERIFY_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid API key")

    data = await request.json()
    try:
        # adapt to Meta payload
        messages = data.get("entry", [])[0].get("changes", [])[0].get("value", {}).get("messages", [])
        if not messages:
            raise HTTPException(status_code=400, detail="No messages found")
        msg_data = messages[0]

        # map nested payload to your MessageSchema
        msg = MessageSchema(
            phone=msg_data.get("from"),
            text=msg_data.get("text", {}).get("body"),
            timestamp=msg_data.get("timestamp")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    process_incoming_message.delay(msg.model_dump())
    return JSONResponse({"status": "enqueued"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)