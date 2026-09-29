"""
Pydantic schemas for payments and webhook payloads.
"""
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

from app.core.constants import PaymentStatus, BookingStatus


class PaymentSimulateRequest(BaseModel):
    booking_id: int = Field(gt=0, description="The booking to process payment for")
    simulate_status: Optional[PaymentStatus] = Field(
        default=PaymentStatus.SUCCESS,
        description="Optionally force payment outcome: SUCCESS or FAILED"
    )
    payment_method: Optional[str] = Field(default="CARD", description="Payment method: CARD, UPI, NETBANKING")


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    payment_reference: str
    booking_id: int
    amount: Decimal
    status: PaymentStatus
    booking_status: BookingStatus
    provider_transaction_id: Optional[str] = None
    failure_reason: Optional[str] = None
    message: str



class WebhookPayload(BaseModel):
    event_id: str = Field(min_length=3, max_length=100, examples=["evt_live_9482749102"])
    event_type: str = Field(default="payment.completed", examples=["payment.completed", "payment.failed"])
    booking_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0)
    status: PaymentStatus = Field(description="Outcome reported by provider: SUCCESS or FAILED")
    provider_transaction_id: Optional[str] = Field(default=None, examples=["txn_mock_392019482"])
    failure_reason: Optional[str] = None


class WebhookResponse(BaseModel):
    status: str
    event_id: str
    booking_id: int
    booking_status: BookingStatus
    message: str
