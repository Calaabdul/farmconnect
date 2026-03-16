import httpx
import sys
from pathlib import Path

# when running this module directly (e.g. python whatsapp_service.py) the
# package root may not be on sys.path, so add it explicitly. this allows
# imports like `from app.config import get_settings` to work without installing
# the package.
root = Path(__file__).parents[2]
sys.path.insert(0, str(root))

# from app.utils import logger
from app.config import get_settings  # noqa: E402 (path added above)

# settings come from root app.config module
settings = get_settings()


class WhatsAppService:
    def __init__(self):
        self.ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN
        self.url = settings.WHATSAPP_API_URL
        self.headers = {
            "Authorization": f"Bearer {self.ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }

        # Production tip: create one shared AsyncClient
        self.client = httpx.AsyncClient(timeout=30)

    async def send_whatsapp_message(self, phone_number, template_name="Hello From FarmConnect!"):
        data = {
            "messaging_product": "whatsapp",
            "to": phone_number,
            "recipient_type": "individual",
            "type": "text",
            "text": {"body": template_name}
        }

        response = await self.client.post(self.url, headers=self.headers, json=data)

        # Print status and response
        print("Status Code:", response.status_code)
        # print("Response:", response.json())

    async def close(self):
        await self.client.aclose()


# Example usage
# import asyncio
# async def main():
#     service = WhatsAppService()
#     await service.send_whatsapp_message(phone_number="+2348140516438")
#     # await service.send_whatsapp_message(phone_number="+2348135194520")
#     await service.close()


# asyncio.run(main())

