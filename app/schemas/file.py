from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class FileUploadResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    is_public: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProfilePictureUploadResponse(BaseModel):
    id: UUID
    url: str
    filename: str
    file_size_bytes: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ProposalAttachmentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class ContractDocumentResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class MilestoneDeliverableResponse(BaseModel):
    id: UUID
    filename: str
    original_filename: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    
    class Config:
        from_attributes = True