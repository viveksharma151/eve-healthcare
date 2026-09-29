"""
Payment domain service handling simulated payments and idempotent webhook processing.
"""
import json
import uuid
from typing import Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.booking import Booking
from app.models.payment import Payment, WebhookEvent
from app.schemas.payment import PaymentSimulateRequest, WebhookPayload
from app.core.constants import BookingStatus, PaymentStatus, WebhookStatus


class PaymentService:
    @staticmethod
    def process_simulated_payment(
        db: Session,
        request: PaymentSimulateRequest,
        user_id: int,
        is_staff: bool = False,
    ) -> Payment:
        """
        Execute simulated payment for a booking with validation and state transitions.
        """
        booking = db.query(Booking).filter(Booking.id == request.booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {request.booking_id} not found",
            )

        # Authorization check: only the booking owner or staff can initiate payment
        if booking.user_id != user_id and not is_staff:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not authorized to pay for this booking",
            )

        if booking.status == BookingStatus.CONFIRMED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This booking has already been confirmed and paid",
            )

        if booking.status == BookingStatus.CANCELLED.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot process payment for a cancelled booking",
            )

        outcome_status = request.simulate_status or PaymentStatus.SUCCESS
        provider_txn_id = f"mock_txn_{uuid.uuid4().hex[:12]}"
        failure_reason = "Simulated bank card decline" if outcome_status == PaymentStatus.FAILED else None

        payment = Payment(
            booking_id=booking.id,
            amount=booking.amount,
            status=outcome_status.value,
            provider_transaction_id=provider_txn_id,
            failure_reason=failure_reason,
        )
        db.add(payment)

        # Transition booking status
        if outcome_status == PaymentStatus.SUCCESS:
            booking.status = BookingStatus.CONFIRMED.value
        else:
            booking.status = BookingStatus.FAILED.value

        db.commit()
        db.refresh(payment)
        db.refresh(booking)
        return payment

    @staticmethod
    def handle_webhook_event(
        db: Session,
        payload: WebhookPayload,
    ) -> Tuple[str, BookingStatus, str]:
        """
        Idempotent webhook handler.
        Guarantees that repeated receipts of the same event_id return safe idempotent responses
        without creating duplicate payments or corrupting the booking state.
        """
        # Step 1: Idempotency check via event_id
        existing_event = db.query(WebhookEvent).filter(WebhookEvent.event_id == payload.event_id).first()
        if existing_event:
            # Event was previously processed; look up current booking status and safely return
            booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
            current_status = BookingStatus(booking.status) if booking else BookingStatus.PENDING
            return (
                "already_processed",
                current_status,
                f"Event '{payload.event_id}' has already been processed. No duplicate mutations performed.",
            )

        # Step 2: Validate booking target
        booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Booking with ID {payload.booking_id} does not exist",
            )

        # Verify amount if applicable
        if payload.amount != booking.amount:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment amount mismatch: payload has {payload.amount}, booking requires {booking.amount}",
            )

        # Step 3: Mutate booking and record payment according to payload outcome
        if payload.status == PaymentStatus.SUCCESS:
            # If already confirmed by another transaction, we don't re-confirm, but record event
            if booking.status != BookingStatus.CONFIRMED.value:
                booking.status = BookingStatus.CONFIRMED.value

            payment = Payment(
                booking_id=booking.id,
                amount=payload.amount,
                status=PaymentStatus.SUCCESS.value,
                provider_transaction_id=payload.provider_transaction_id or f"webhook_txn_{uuid.uuid4().hex[:10]}",
                failure_reason=None,
            )
            db.add(payment)
            message = "Payment processed successfully and booking confirmed."
        else:
            if booking.status == BookingStatus.PENDING.value:
                booking.status = BookingStatus.FAILED.value

            payment = Payment(
                booking_id=booking.id,
                amount=payload.amount,
                status=PaymentStatus.FAILED.value,
                provider_transaction_id=payload.provider_transaction_id or f"webhook_fail_{uuid.uuid4().hex[:10]}",
                failure_reason=payload.failure_reason or "Provider reported transaction failure",
            )
            db.add(payment)
            message = "Payment failure recorded and booking updated to FAILED."

        # Step 4: Record WebhookEvent in ledger to guarantee future idempotency
        webhook_record = WebhookEvent(
            event_id=payload.event_id,
            event_type=payload.event_type,
            booking_id=booking.id,
            payload=json.dumps(payload.model_dump(), default=str),
            status=WebhookStatus.PROCESSED.value,
        )
        db.add(webhook_record)

        db.commit()
        db.refresh(booking)

        return "processed", BookingStatus(booking.status), message
