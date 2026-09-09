from pydantic import BaseModel

class SessionResponse(BaseModel):
    id: int
    device_name: str | None
    user_agent: str | None
    ip_address: str | None
    created_at: str
    last_used_at: str
    expires_at: str
    is_active: bool

    class Config:
        from_attributes = True