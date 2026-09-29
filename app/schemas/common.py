"""
Common schemas for pagination and standard responses.
"""
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str
    detail: str = ""


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int = Field(ge=1, default=1)
    page_size: int = Field(ge=1, le=100, default=20)
