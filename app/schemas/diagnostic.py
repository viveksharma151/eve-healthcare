"""
Pydantic schemas for Diagnostic Centres and Tests.
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class DiagnosticTestCreate(BaseModel):
    code: str = Field(min_length=2, max_length=50, examples=["CBC"])
    name: str = Field(min_length=2, max_length=255, examples=["Complete Blood Count"])
    description: Optional[str] = Field(default=None, examples=["Evaluates overall health and detects wide range of disorders."])


class DiagnosticTestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str] = None
    created_at: datetime


class CentreTestOffer(BaseModel):
    test_id: int
    price: Decimal = Field(gt=0, decimal_places=2, examples=[500.00])
    is_available: bool = True


class AvailableTestItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    test_id: int
    code: str
    name: str
    description: Optional[str] = None
    price: Decimal
    is_available: bool


class DiagnosticCentreCreate(BaseModel):
    name: str = Field(min_length=2, max_length=255, examples=["CareMax Diagnostics - Indiranagar"])
    location: str = Field(min_length=2, max_length=255, examples=["Indiranagar, Bangalore"])
    contact_phone: Optional[str] = Field(default=None, max_length=50, examples=["+91 9876543210"])
    initial_tests: Optional[List[CentreTestOffer]] = Field(default_factory=list)


class DiagnosticCentreUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    contact_phone: Optional[str] = None
    is_active: Optional[bool] = None


class DiagnosticCentreResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    location: str
    contact_phone: Optional[str] = None
    is_active: bool
    created_at: datetime
    available_tests: List[AvailableTestItem] = Field(default_factory=list)

