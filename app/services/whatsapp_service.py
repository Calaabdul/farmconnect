import httpx
from app.config import get_settings
from app.utils.logger import logger

settings = get_settings()

# Shared AsyncClient to avoid creating one per request. Closed on app shutdown.
_shared_client: httpx.AsyncClient | None = None


def get_shared_client() -> httpx.AsyncClient:
    global _shared_client
    if _shared_client is None:
        _shared_client = httpx.AsyncClient(timeout=30)
    return _shared_client


async def close_shared_client() -> None:
    global _shared_client
    if _shared_client is not None:
        await _shared_client.aclose()
        _shared_client = None


class WhatsAppService:
    def __init__(self):
        self.ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
        self.url = settings.WHATSAPP_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        self.client = get_shared_client()

    async def send_whatsapp_message(
        self, phone_number: str, template_name: str = "Hello From FarmConnect!"
    ):
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "recipient_type": "individual",
            "type": "text",
            "text": {"body": template_name},
        }

        try:
            response = await self.client.post(self.url, headers=self.headers, json=data)
            # Basic error handling
            if response.status_code >= 400:
                body = await response.aread()
                logger.error("WhatsApp error %s %s", response.status_code, body)
            else:
                logger.info(
                    "WhatsApp message sent to %s (status %s)", phone_number, response.status_code
                )
        except Exception as e:
            logger.exception("WhatsApp request failed: %s", e)


# if __name__ == "__main__":
#     # Quick test to verify client works
#     import asyncio

#     async def test():
#         service = WhatsAppService()
#         await service.send_whatsapp_message("+2348140516438", "Test message")

#     asyncio.run(test())
