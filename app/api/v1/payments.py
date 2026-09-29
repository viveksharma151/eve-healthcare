"""
Payment endpoints: Simulated payment processing and idempotent webhook receiver.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.booking import Booking
from app.schemas.payment import (
    PaymentSimulateRequest,
    PaymentResponse,
    WebhookPayload,
    WebhookResponse,
)
from app.services.payment_service import PaymentService
from app.core.constants import BookingStatus, PaymentStatus

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post("/", response_model=PaymentResponse, status_code=status.HTTP_200_OK)
def simulate_payment(
    payload: PaymentSimulateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Simulate payment processing for a booking.
    Updates the booking to CONFIRMED on SUCCESS or FAILED on card decline.
    """
    payment = PaymentService.process_simulated_payment(
        db=db,
        request=payload,
        user_id=current_user.id,
        is_staff=current_user.is_staff,
    )

    booking = db.query(Booking).filter(Booking.id == payment.booking_id).first()
    booking_status = BookingStatus(booking.status)

    msg = (
        "Simulated payment succeeded and booking confirmed."
        if payment.status == PaymentStatus.SUCCESS.value
        else "Simulated payment failed and booking marked as failed."
    )

    return PaymentResponse(
        payment_reference=payment.payment_reference,
        booking_id=payment.booking_id,
        amount=payment.amount,
        status=PaymentStatus(payment.status),
        booking_status=booking_status,
        provider_transaction_id=payment.provider_transaction_id,
        failure_reason=payment.failure_reason,
        message=msg,
    )


@router.post("/webhook/", response_model=WebhookResponse, status_code=status.HTTP_200_OK)
def payment_webhook(
    payload: WebhookPayload,
    db: Session = Depends(get_db),
):
    """
    Receive asynchronous payment-status updates from the simulated provider.
    Enforces strict idempotency based on unique `event_id`.
    """
    result_status, booking_status, message = PaymentService.handle_webhook_event(
        db=db,
        payload=payload,
    )

    return WebhookResponse(
        status=result_status,
        event_id=payload.event_id,
        booking_id=payload.booking_id,
        booking_status=booking_status,
        message=message,
    )
