"""
Models for payments and webhook idempotency tracking.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.constants import PaymentStatus, WebhookStatus


def generate_payment_reference() -> str:
    """Generate a readable payment transaction reference, e.g., PAY-4B6E1F."""
    return f"PAY-{uuid.uuid4().hex[:8].upper()}"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    payment_reference = Column(String(32), unique=True, index=True, default=generate_payment_reference, nullable=False)
    booking_id = Column(Integer, ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default=PaymentStatus.PENDING.value, nullable=False, index=True)
    provider_transaction_id = Column(String(100), nullable=True, index=True)
    failure_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    booking = relationship("Booking", back_populates="payments")


class WebhookEvent(Base):
    """
    Idempotency ledger for incoming webhook events.
    Ensures that processing an event twice will not result in duplicate state mutations.
    """
    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    event_type = Column(String(50), nullable=False)
    booking_id = Column(Integer, nullable=True, index=True)
    payload = Column(Text, nullable=False)
    status = Column(String(20), default=WebhookStatus.PROCESSED.value, nullable=False)
    received_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
