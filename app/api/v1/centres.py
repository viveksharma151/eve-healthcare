"""
Diagnostic Centres endpoints: Create, retrieve, and configure centres and their offered tests/pricing.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.diagnostic import DiagnosticCentre, DiagnosticTest, CentreTest
from app.schemas.diagnostic import (
    DiagnosticCentreCreate,
    DiagnosticCentreUpdate,
    DiagnosticCentreResponse,
    AvailableTestItem,
    CentreTestOffer,
)

router = APIRouter(prefix="/centres", tags=["Diagnostic Centres"])


def _build_centre_response(centre: DiagnosticCentre) -> DiagnosticCentreResponse:
    """Helper to convert a DiagnosticCentre ORM object with centre_tests into response schema."""
    available_tests = []
    for ct in centre.centre_tests:
        if ct.test:
            available_tests.append(
                AvailableTestItem(
                    test_id=ct.test.id,
                    code=ct.test.code,
                    name=ct.test.name,
                    description=ct.test.description,
                    price=ct.price,
                    is_available=ct.is_available,
                )
            )

    return DiagnosticCentreResponse(
        id=centre.id,
        name=centre.name,
        location=centre.location,
        contact_phone=centre.contact_phone,
        is_active=centre.is_active,
        created_at=centre.created_at,
        available_tests=available_tests,
    )


@router.post("/", response_model=DiagnosticCentreResponse, status_code=status.HTTP_201_CREATED)
def create_diagnostic_centre(
    payload: DiagnosticCentreCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new diagnostic centre and optionally associate initial tests with pricing.
    """
    centre = DiagnosticCentre(
        name=payload.name.strip(),
        location=payload.location.strip(),
        contact_phone=payload.contact_phone.strip() if payload.contact_phone else None,
        is_active=True,
    )
    db.add(centre)
    db.flush()  # assign centre.id

    if payload.initial_tests:
        for item in payload.initial_tests:
            test = db.query(DiagnosticTest).filter(DiagnosticTest.id == item.test_id).first()
            if not test:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Diagnostic test with ID {item.test_id} does not exist",
                )
            centre_test = CentreTest(
                centre_id=centre.id,
                test_id=item.test_id,
                price=item.price,
                is_available=item.is_available,
            )
            db.add(centre_test)

    db.commit()
    db.refresh(centre)
    return _build_centre_response(centre)


@router.get("/", response_model=List[DiagnosticCentreResponse])
def list_diagnostic_centres(
    location: Optional[str] = Query(None, description="Filter by location (e.g. Indiranagar, Bangalore)"),
    test_id: Optional[int] = Query(None, description="Filter centres offering a specific test ID"),
    q: Optional[str] = Query(None, description="Search centres by name"),
    only_active: bool = Query(True, description="Return only active centres"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Retrieve diagnostic centres with filtering by location, test availability, and search terms.
    """
    query = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.centre_tests).joinedload(CentreTest.test))
    )

    if only_active:
        query = query.filter(DiagnosticCentre.is_active == True)

    if location:
        query = query.filter(DiagnosticCentre.location.ilike(f"%{location.strip()}%"))

    if q:
        query = query.filter(DiagnosticCentre.name.ilike(f"%{q.strip()}%"))

    if test_id is not None:
        query = query.join(DiagnosticCentre.centre_tests).filter(
            CentreTest.test_id == test_id,
            CentreTest.is_available == True,
        )

    centres = query.distinct().offset(offset).limit(limit).all()
    return [_build_centre_response(c) for c in centres]


@router.get("/{centre_id}", response_model=DiagnosticCentreResponse)
def get_diagnostic_centre(centre_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information for a diagnostic centre including all offered tests and pricing.
    """
    centre = (
        db.query(DiagnosticCentre)
        .options(joinedload(DiagnosticCentre.centre_tests).joinedload(CentreTest.test))
        .filter(DiagnosticCentre.id == centre_id)
        .first()
    )
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic centre with ID {centre_id} not found",
        )
    return _build_centre_response(centre)


@router.post("/{centre_id}/tests", response_model=DiagnosticCentreResponse)
def add_or_update_centre_test(
    centre_id: int,
    offer: CentreTestOffer,
    db: Session = Depends(get_db),
):
    """
    Configure a diagnostic test offering and price for a specific centre.
    """
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic centre with ID {centre_id} not found",
        )

    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == offer.test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic test with ID {offer.test_id} not found",
        )

    centre_test = (
        db.query(CentreTest)
        .filter(CentreTest.centre_id == centre_id, CentreTest.test_id == offer.test_id)
        .first()
    )

    if centre_test:
        centre_test.price = offer.price
        centre_test.is_available = offer.is_available
    else:
        centre_test = CentreTest(
            centre_id=centre_id,
            test_id=offer.test_id,
            price=offer.price,
            is_available=offer.is_available,
        )
        db.add(centre_test)

    db.commit()
    db.refresh(centre)
    return _build_centre_response(centre)


@router.put("/{centre_id}", response_model=DiagnosticCentreResponse)
def update_diagnostic_centre(
    centre_id: int,
    payload: DiagnosticCentreUpdate,
    db: Session = Depends(get_db),
):
    """
    Update centre details such as name, location, contact phone, or active status.
    """
    centre = db.query(DiagnosticCentre).filter(DiagnosticCentre.id == centre_id).first()
    if not centre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic centre with ID {centre_id} not found",
        )

    if payload.name is not None:
        centre.name = payload.name.strip()
    if payload.location is not None:
        centre.location = payload.location.strip()
    if payload.contact_phone is not None:
        centre.contact_phone = payload.contact_phone.strip()
    if payload.is_active is not None:
        centre.is_active = payload.is_active

    db.commit()
    db.refresh(centre)
    return _build_centre_response(centre)
