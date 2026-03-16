from __future__ import annotations

from datetime import datetime
from typing import Optional, Any, List

from pydantic import BaseModel, Field, UUID4, ConfigDict


class UserBase(BaseModel):
    phone: str
    role: str
    location: Optional[str] = None


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListingBase(BaseModel):
    product_name: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    description: Optional[str] = None
    metadata: Optional[Any] = None


class ListingCreate(ListingBase):
    pass


class Listing(ListingBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BuyerRequestBase(BaseModel):
    product_name: str
    max_price: Optional[float] = None
    quantity: Optional[float] = None
    metadata: Optional[Any] = None


class BuyerRequestCreate(BuyerRequestBase):
    pass


class BuyerRequest(BuyerRequestBase):
    id: UUID4
    user_id: UUID4
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Match(BaseModel):
    id: UUID4
    user_id: UUID4
    other_user_id: UUID4
    listing_id: Optional[UUID4] = None
    buyer_request_id: Optional[UUID4] = None
    match_data: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageSchema(BaseModel):
    phone: str
    text: str
    timestamp: Optional[datetime] = None


class TaskContext(BaseModel):
    user_id: Optional[UUID4] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    raw_message: Optional[str] = None
    intent: Optional[str] = None
    confidence: Optional[float] = None
    extracted: Optional[dict[str, Any]] = None


class IntentResult(BaseModel):
    intent: str
    confidence: float


class ExtractionResult(BaseModel):
    role: Optional[str] = None
    product_name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[float] = None
    max_price: Optional[float] = None
    description: Optional[str] = None
    location: Optional[str] = None


class GuardrailResult(BaseModel):
    is_safe: bool
    reason: Optional[str] = None
