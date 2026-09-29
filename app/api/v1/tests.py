"""
Diagnostic Tests endpoints: Create and retrieve tests from the catalog.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.diagnostic import DiagnosticTest
from app.schemas.diagnostic import DiagnosticTestCreate, DiagnosticTestResponse

router = APIRouter(prefix="/tests", tags=["Diagnostic Tests"])


@router.post("/", response_model=DiagnosticTestResponse, status_code=status.HTTP_201_CREATED)
def create_diagnostic_test(
    payload: DiagnosticTestCreate,
    db: Session = Depends(get_db),
):
    """
    Register a new diagnostic test in the master catalog.
    """
    clean_code = payload.code.strip().upper()
    existing = db.query(DiagnosticTest).filter(DiagnosticTest.code == clean_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test code '{clean_code}' already exists.",
        )

    test = DiagnosticTest(
        code=clean_code,
        name=payload.name.strip(),
        description=payload.description.strip() if payload.description else None,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


@router.get("/", response_model=List[DiagnosticTestResponse])
def list_diagnostic_tests(
    q: Optional[str] = Query(None, description="Search by test name or code"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    List all available diagnostic tests with optional search.
    """
    query = db.query(DiagnosticTest)
    if q:
        search_filter = f"%{q.strip()}%"
        query = query.filter(
            (DiagnosticTest.name.ilike(search_filter)) | (DiagnosticTest.code.ilike(search_filter))
        )
    return query.offset(offset).limit(limit).all()


@router.get("/{test_id}", response_model=DiagnosticTestResponse)
def get_diagnostic_test(test_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information for a single diagnostic test.
    """
    test = db.query(DiagnosticTest).filter(DiagnosticTest.id == test_id).first()
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diagnostic test with ID {test_id} not found",
        )
    return test
