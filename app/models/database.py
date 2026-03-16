import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Float,
    Integer,
    ForeignKey,
    JSON,
    Boolean,
    DECIMAL,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class UserRole(Enum):
    BUYER = "buyer"
    SELLER = "seller"
    UNKNOWN = "unknown"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone = Column(String, unique=True, nullable=False, index=True)
    role = Column(
        String, nullable=False, default=UserRole.UNKNOWN.value
    )  # use enum values
    location = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    listings = relationship("Listing", back_populates="user")
    buyer_requests = relationship("BuyerRequest", back_populates="user")
    matches = relationship("Match", back_populates="user")


class Listing(Base):
    __tablename__ = "listings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product_name = Column(String, nullable=False)
    price = Column(DECIMAL(precision=10, scale=2), nullable=True)
    quantity = Column(Float, nullable=True)
    description = Column(String, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="listings")


class BuyerRequest(Base):
    __tablename__ = "buyer_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    product_name = Column(String, nullable=False)
    max_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=True)
    extra_data = Column(JSONB, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="buyer_requests")

class Match(Base):
    __tablename__ = "matches"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    other_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    listing_id = Column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True)
    buyer_request_id = Column(UUID(as_uuid=True), ForeignKey("buyer_requests.id"), nullable=True)
    match_data = Column(JSONB, nullable=True)
    notified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    # specify which FK each relationship refers to
    user = relationship("User", foreign_keys=[user_id], back_populates="matches")
    other_user = relationship("User", foreign_keys=[other_user_id])