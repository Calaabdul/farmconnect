from __future__ import annotations

import asyncio

from pydantic import ValidationError

from app.models.schemas import MessageSchema, TaskContext
from app.services.whatsapp_service import WhatsAppService
from app.database.connection import AsyncSessionLocal
from app.models.database import User, Listing, BuyerRequest, Match
from sqlalchemy import select
from app.services.agents import create_standard_pipeline
from app.services.llm_service import LLMService
from app.utils.logger import setup_logger
from app.config import get_settings

settings = get_settings()

logger = setup_logger()


async def _send_greeting(whatsapp: WhatsAppService, phone: str):
    """Send initial greeting to user when they first contact the bot."""
    await whatsapp.send_whatsapp_message(
        phone_number=phone, template_name="Welcome to Farm Connect 🌾"
    )


async def _send_whatsapp_message(
    whatsapp: WhatsAppService, phone: str, message: str = ""
):
    """Send a WhatsApp message asynchronously to the given phone number."""
    await whatsapp.send_whatsapp_message(phone_number=phone, template_name=message)


async def _deliver_contacts(msg_phone: str) -> list[str]:
    """Retrieve pending contacts for a user who confirmed."""
    async with AsyncSessionLocal() as session:
        # find user using ORM select
        stmt = select(User).where(User.phone == msg_phone)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return []

        # find matches for user
        stmt = (
            select(Match, User)
            .join(User, User.id == Match.other_user_id)
            .where(Match.user_id == user.id, Match.notified == 0)
        )
        results = await session.execute(stmt)
        contacts = []
        for match, other in results.all():
            contacts.append(other.phone)
            match.notified = 1
            session.add(match)
        await session.commit()
        return contacts


async def _store_user_and_match(context: TaskContext, msg_phone: str):
    """Store user and listing/buyer request using async session."""
    async with AsyncSessionLocal() as session:
        # upsert user by phone
        result = await session.execute(
            User.__table__.select().where(User.phone == msg_phone)
        )
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                phone=msg_phone,
                role=context.extracted.get("role", "unknown"),
                location=context.extracted.get("location"),
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

        role = context.extracted.get("role")
        if role == "farmer":
            listing = Listing(
                user_id=user.id,
                product_name=context.extracted.get("product_name", ""),
                price=context.extracted.get("price"),
                quantity=context.extracted.get("quantity"),
                description=context.extracted.get("description"),
                extra_data=context.extracted,
            )
            session.add(listing)
            await session.commit()
            await session.refresh(listing)

            # attempt matching with existing buyer requests
            stmt = select(BuyerRequest).where(
                BuyerRequest.product_name == listing.product_name,
            )
            results = await session.execute(stmt)
            for br in results.scalars().all():
                # price criteria
                if (
                    br.max_price is None
                    or listing.price is None
                    or listing.price <= br.max_price
                ):
                    match = Match(
                        user_id=user.id,
                        other_user_id=br.user_id,
                        listing_id=listing.id,
                        buyer_request_id=br.id,
                        match_data={"type": "listing_to_buyer"},
                    )
                    session.add(match)
            await session.commit()
        elif role == "buyer":
            buyer_req = BuyerRequest(
                user_id=user.id,
                product_name=context.extracted.get("product_name", ""),
                max_price=context.extracted.get("max_price"),
                quantity=context.extracted.get("quantity"),
                extra_data=context.extracted,
            )
            session.add(buyer_req)
            await session.commit()
            await session.refresh(buyer_req)

            # attempt matching with existing listings
            stmt = select(Listing).where(
                Listing.product_name == buyer_req.product_name,
            )
            results = await session.execute(stmt)
            for ls in results.scalars().all():
                if (
                    buyer_req.max_price is None
                    or ls.price is None
                    or ls.price <= buyer_req.max_price
                ):
                    match = Match(
                        user_id=user.id,
                        other_user_id=ls.user_id,
                        listing_id=ls.id,
                        buyer_request_id=buyer_req.id,
                        match_data={"type": "buyer_to_listing"},
                    )
                    session.add(match)
            await session.commit()


async def process_incoming_message(raw: dict):
    """Background handler for handling an incoming WhatsApp message.

    The workflow is:
    1. Validate payload and build a TaskContext.
    2. Send initial greeting "Hello this is FarmConnect".
    3. If the message is a confirmation ("yes"), deliver contacts and return.
    4. Run guardrail, intent and extraction agents.
    5. Persist user and listing/buyer request and attempt matching.
    6. Send a response back via WhatsApp.

    Note: This handler processes incoming messages; each user sends a message
    and the bot replies with a greeting before agents take over.
    """

    try:
        msg = MessageSchema(**raw)
    except ValidationError:
        return

    context = TaskContext(raw_message=msg.text, phone=msg.phone)
    whatsapp = WhatsAppService()

    # Send initial greeting (fire-and-forget via background processing inside
    # the task). Use keyword args to avoid signature confusion.
    await _send_greeting(whatsapp=whatsapp, phone=msg.phone)

    # if user is confirming, deliver any pending contacts
    if msg.text.strip().lower() in ("yes", "y"):
        contacts = await _deliver_contacts(msg.phone)
        if contacts:
            await _send_whatsapp_message(
                whatsapp,
                msg.phone,
                f"Here are contact numbers: {', '.join(contacts)}",
            )
        else:
            await _send_whatsapp_message(
                whatsapp, msg.phone, "No new contacts available."
            )
        return

    # run agent pipeline (guardrail, intent, extraction)
    try:
        pipeline = create_standard_pipeline(context)
        context = await pipeline.run(context)
    except Exception as e:
        logger.exception("Agent pipeline failed: %s", e)
        # If the agent pipeline fails (LLM error), send a polite apology.
        await _send_whatsapp_message(
            whatsapp, msg.phone, "Sorry, I cannot help you at this moment."
        )
        return

    # store user & listing/buyer request and perform matching
    await _store_user_and_match(context, msg.phone)

    # Generate a human-friendly reply using the LLM and send it
    try:
        llm = LLMService()
        prompt = (
            f"You are an assistant for FarmConnect. The user said: '{context.raw_message}'. "
            f"Extracted data: {context.extracted}. Return a short WhatsApp message confirming receipt and next steps."
        )
        reply = await llm.call_raw(prompt)
        if not reply:
            reply = "Thank you — your message was processed. We'll be in touch."
        await _send_whatsapp_message(whatsapp, msg.phone, reply)
    except Exception as e:
        logger.exception("Failed to generate/send LLM reply: %s", e)
        await _send_whatsapp_message(
            whatsapp, msg.phone, "Thank you! Your message has been processed."
        )


# Provide a `.delay` compatibility attribute so existing callers/tests that
# expect `process_incoming_message.delay(...)` continue to work.  In
# production the FastAPI endpoint will prefer background tasks when
# Celery is not configured.
def _delay_wrapper(payload: dict):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        # No running loop — run synchronously
        return asyncio.run(process_incoming_message(payload))
    else:
        # schedule in the running loop
        return asyncio.create_task(process_incoming_message(payload))


process_incoming_message.delay = _delay_wrapper


# Provide a `.delay` compatibility attribute so existing callers/tests that
# expect `process_incoming_message.delay(...)` continue to work.  In
# production the FastAPI endpoint will prefer background tasks when
# Celery is not configured.
def _sync_delay(payload: dict):
    return process_incoming_message(payload)


process_incoming_message.delay = _sync_delay
