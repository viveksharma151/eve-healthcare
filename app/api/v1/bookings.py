"""
Diagnostic Test Booking endpoints with authentication, authorization checks, and lifecycle transitions.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest, CentreTest
from app.models.booking import Booking
from app.schemas.booking import BookingCreate, BookingResponse
from app.core.constants import BookingStatus

router = APIRouter(prefix="/bookings", tags=["Bookings"])


def _to_booking_response(booking: Booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        booking_reference=booking.booking_reference,
        user_id=booking.user_id,
        centre_id=booking.centre_id,
        test_id=booking.test_id,
        centre_name=booking.centre.name if booking.centre else None,
        centre_location=booking.centre.location if booking.centre else None,
        test_name=booking.test.name if booking.test else None,
        appointment_datetime=booking.appointment_datetime,
        amount=booking.amount,
        status=BookingStatus(booking.status),
        notes=booking.notes,
        created_at=booking.created_at,
        updated_at=booking.updated_at,
    )


@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Book a diagnostic test at a specific centre for the authenticated user.
    Calculates authoritative price from the centre's catalog.
    """
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == payload.centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic centre with ID {payload.centre_id} not found",
        )
    if not centre.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The selected diagnostic centre is currently inactive",
        )

    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == payload.test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic test with ID {payload.test_id} not found",
        )

    centre_test = (
        db.query(CentreTest)
        .filter(CentreTest.centre_id == payload.centre_id, CentreTest.test_id == payload.test_id)
        .first()
    )
    if not centre_test or not centre_test.is_available:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Diagnostic test '{test.name}' is not currently available at centre '{centre.name}'",
        )

    # Clean timezone if naive
    appt_dt = payload.appointment_datetime.replace(tzinfo=None)

    booking = Booking(
        user_id=current_user.id,
        centre_id=centre.id,
        test_id=test.id,
        appointment_datetime=appt_dt,
        amount=centre_test.price,
        status=BookingStatus.PENDING.value,
        notes=payload.notes,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Eager load relationships for response
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
        .filter(Booking.id == booking.id)
        .first()
    )
    return _to_booking_response(booking)


@router.get("/", response_model=List[BookingResponse])
def list_bookings(
    status_filter: Optional[BookingStatus] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List bookings for the authenticated user. Staff members can view all bookings.
    """
    query = (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
    )

    if not current_user.is_staff:
        query = query.filter(Booking.user_id == current_user.id)

    if status_filter:
        query = query.filter(Booking.status == status_filter.value)

    bookings = query.order_by(Booking.created_at.desc()).offset(offset).limit(limit).all()
    return [_to_booking_response(b) for b in bookings]


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve booking details with ownership verification.
    """
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found",
        )

    # Authorization check
    if booking.user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to access this booking",
        )

    return _to_booking_response(booking)


@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Cancel a booking with authorization checks and state validation.
    """
    booking = (
        db.query(Booking)
        .options(joinedload(Booking.centre), joinedload(Booking.test))
        .filter(Booking.id == booking_id)
        .first()
    )
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Booking with ID {booking_id} not found",
        )

    # Authorization check
    if booking.user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to cancel this booking",
        )

    if booking.status == BookingStatus.CANCELLED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Booking is already cancelled",
        )

    if booking.status == BookingStatus.FAILED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a booking that has already failed",
        )

    booking.status = BookingStatus.CANCELLED.value
    db.commit()
    db.refresh(booking)
    return _to_booking_response(booking)
