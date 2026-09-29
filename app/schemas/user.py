"""
Pydantic schemas for user signup, authentication, and responses.
"""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=2, max_length=100)
    password: str = Field(min_length=6, max_length=128, description="Minimum 6 characters")


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    is_staff: bool
    created_at: datetime



class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
