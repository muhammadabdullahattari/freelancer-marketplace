from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from uuid import UUID


class UserResponse(BaseModel):
    id: UUID 
    name: str
    username: str
    email: EmailStr
    first_name: str | None
    last_name: str | None
    phone_number: str | None
    is_active: bool
    is_verified: bool
    role: str 
    model_config = {"from_attributes": True}


class UserRead(BaseModel):
    id: UUID 
    name: str
    email: EmailStr
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    first_name: str
    last_name: str
    phone_number: str = Field(pattern=r"^03\d{9}$",description="Pakistani mobile number, e.g. 03001234567")
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        value = value.strip()

        if not value.isdigit():
            raise ValueError("Phone number must contain only digits")

        if len(value) != 11:
            raise ValueError("Phone number must contain exactly 11 digits")

        if not value.startswith("03"):
            raise ValueError("Phone number must start with 03")

        return value
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

class UserPatch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone_number: Optional[str] = Field(pattern=r"^03\d{9}$",description="Pakistani mobile number, e.g. 03001234567")
    
    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value: str) -> str:
        value = value.strip()

        if not value.isdigit():
            raise ValueError("Phone number must contain only digits")

        if len(value) != 11:
            raise ValueError("Phone number must contain exactly 11 digits")

        if not value.startswith("03"):
            raise ValueError("Phone number must start with 03")

        return value
    
    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value