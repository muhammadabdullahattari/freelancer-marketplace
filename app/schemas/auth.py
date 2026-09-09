from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Literal

class UserCreate(BaseModel):
    first_name: str = Field(min_length=2,max_length=100)
    last_name: str = Field(min_length=2,max_length=100)
    username: str = Field(min_length=3,max_length=30)
    email: EmailStr
    password: str = Field(min_length=8,max_length=128)
    role: Literal["CLIENT", "FREELANCER"] = Field(default="CLIENT OR FREELANCER",description="Select user type: CLIENT for uploading projects, FREELANCER for get projects/work")

    @field_validator("first_name", "last_name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Name cannot be empty")

        return value

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        value = value.strip().lower()
        if not value.replace("_", "").isalnum():
            raise ValueError("Username can contain only letters, numbers and underscores")

        return value
    
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> EmailStr:
        return str(value).strip().lower()
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not any(char.isalpha() for char in value):
            raise ValueError("Password must contain at least one letter")

        if not any(char.isdigit() for char in value):
            raise ValueError("Password must contain at least one number")

        if not any(not char.isalnum() for char in value):
            raise ValueError("Password must contain at least one special character")

        return value
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        valid_roles = ["CLIENT", "FREELANCER"]
        if value not in valid_roles:
            raise ValueError(f"Role must be one of {valid_roles}")
        return value
    
class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class Token(BaseModel):
    access_token: str
    refresh_token : str
    token_type: str
    user_id: str
    username: str
    role: str
    
class Refresh_Token(BaseModel):
    access_token: str
    token_type: str
    
class LoginRequest(BaseModel):
    email: str
    password: str
    
    
class SessionInfo(BaseModel):
    valid: bool
    user_id: str
    username: str
    role: str


class SessionResponse(BaseModel):
    message: str
    session_cleared: bool