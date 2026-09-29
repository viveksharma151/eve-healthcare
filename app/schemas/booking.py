"""
Pydantic schemas for test bookings.
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict

from app.core.constants import BookingStatus


class BookingCreate(BaseModel):
    centre_id: int = Field(gt=0, description="ID of diagnostic centre")
    test_id: int = Field(gt=0, description="ID of diagnostic test to book")
    appointment_datetime: datetime = Field(
        description="Scheduled appointment date & time (must be in the future, ISO-8601)"
    )
    notes: Optional[str] = Field(default=None, max_length=500, description="Patient notes or symptoms")

    @field_validator("appointment_datetime")
    @classmethod
    def validate_future_datetime(cls, v: datetime) -> datetime:
        # Normalize timezone-aware vs naive
        now = datetime.now(timezone.utc)
        target = v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        if target <= now:
            raise ValueError("Appointment date and time must be in the future")
        return v


class BookingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_reference: str
    user_id: int
    centre_id: int
    test_id: int
    centre_name: Optional[str] = None
    centre_location: Optional[str] = None
    test_name: Optional[str] = None
    appointment_datetime: datetime
    amount: Decimal
    status: BookingStatus
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime



class BookingStatusUpdate(BaseModel):
    status: BookingStatus
