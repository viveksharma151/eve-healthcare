"""
Booking model for diagnostic appointments.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.core.constants import BookingStatus


def generate_booking_reference() -> str:
    """Generate a clean, readable reference code for users, e.g., BK-9D2F4A."""
    return f"BK-{uuid.uuid4().hex[:8].upper()}"


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    booking_reference = Column(String(32), unique=True, index=True, default=generate_booking_reference, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    centre_id = Column(Integer, ForeignKey("diagnostic_centres.id"), nullable=False, index=True)
    test_id = Column(Integer, ForeignKey("diagnostic_tests.id"), nullable=False, index=True)
    appointment_datetime = Column(DateTime, nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String(20), default=BookingStatus.PENDING.value, nullable=False, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    user = relationship("User", back_populates="bookings")
    centre = relationship("DiagnosticCentre", back_populates="bookings")
    test = relationship("DiagnosticTest", back_populates="bookings")
    payments = relationship("Payment", back_populates="booking", cascade="all, delete-orphan")
