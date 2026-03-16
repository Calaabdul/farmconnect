from __future__ import annotations

import asyncio
from celery import shared_task
from pydantic import ValidationError

from app.models.schemas import MessageSchema, TaskContext
from app.services.whatsapp_service import WhatsAppService
from app.database.connection import AsyncSessionLocal
from app.models.database import User, Listing, BuyerRequest, Match
from sqlalchemy import select
from app.services.agents import create_standard_pipeline


async def _send_greeting(phone: str, whatsapp: WhatsAppService):
    """Send initial greeting to user when they first contact the bot."""
    await whatsapp.send_whatsapp_message(
        phone_number=phone, template_name="Hello this is FarmConnect!"
    )


async def _send_whatsapp_message(whatsapp: WhatsAppService, phone: str, message: str):
    """Send a WhatsApp message asynchronously."""
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


@shared_task
def process_incoming_message(raw: dict):
    """Celery task for handling an incoming WhatsApp message.

    The workflow is:
    1. Validate payload and build a TaskContext.
    2. Send initial greeting "Hello this is FarmConnect".
    3. If the message is a confirmation ("yes"), deliver contacts and return.
    4. Run guardrail, intent and extraction agents.
    5. Persist user and listing/buyer request and attempt matching.
    6. Send a response back via WhatsApp.

    Note: This task handles multiple users, each user sends a message first
    before the bot starts replying with the greeting, then agents take over.
    """

    async def _handle_message(raw_payload: dict):
        try:
            msg = MessageSchema(**raw_payload)
        except ValidationError:
            return

        context = TaskContext(raw_message=msg.text, phone=msg.phone)
        whatsapp = WhatsAppService()

        # Send initial greeting
        await _send_greeting(msg.phone, whatsapp)

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
        except Exception:
            await _send_whatsapp_message(
                whatsapp, msg.phone, "Sorry, I cannot help you at this moment."
            )
            return

        # store user & listing/buyer request and perform matching
        await _store_user_and_match(context, msg.phone)

        # send confirmation message
        await _send_whatsapp_message(
            whatsapp, msg.phone, "Thank you! Your message has been processed."
        )

    # Run the whole async flow once per task to avoid repeated event loop creation
    asyncio.run(_handle_message(raw))
