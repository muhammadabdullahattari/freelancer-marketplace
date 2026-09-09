from app.core.config import settings
from enum import Enum

class FileType(str, Enum):
    PROFILE_PICTURE = "profile_picture"
    PROPOSAL_ATTACHMENT = "proposal_attachment"
    CONTRACT_DOCUMENT = "contract_document"
    MILESTONE_DELIVERABLE = "milestone_deliverable"


class FileConfig:
    
    CONFIGS = {
        FileType.PROFILE_PICTURE: {
            "bucket": settings.SUPABASE_STORAGE_BUCKET_PROFILES,
            "max_size_mb": settings.MAX_PROFILE_PICTURE_SIZE_MB,
            "allowed_types": settings.ALLOWED_IMAGE_TYPES,
            "is_public": True,
            "folder": "user-profiles"
        },
        FileType.PROPOSAL_ATTACHMENT: {
            "bucket": settings.SUPABASE_STORAGE_BUCKET_PROPOSALS,
            "max_size_mb": settings.MAX_PROPOSAL_ATTACHMENT_SIZE_MB,
            "allowed_types": settings.ALLOWED_FILE_TYPES,
            "is_public": False,
            "folder": "proposals"
        },
        FileType.CONTRACT_DOCUMENT: {
            "bucket": settings.SUPABASE_STORAGE_BUCKET_CONTRACTS,
            "max_size_mb": settings.MAX_CONTRACT_DOCUMENT_SIZE_MB,
            "allowed_types": settings.ALLOWED_DOCUMENT_TYPES,
            "is_public": False,
            "folder": "contracts"
        },
        FileType.MILESTONE_DELIVERABLE: {
            "bucket": settings.SUPABASE_STORAGE_BUCKET_MILESTONES,
            "max_size_mb": settings.MAX_MILESTONE_DELIVERABLE_SIZE_MB,
            "allowed_types": settings.ALLOWED_FILE_TYPES,
            "is_public": False,
            "folder": "milestones"
        }
    }
    
    @staticmethod
    def get_config(file_type: FileType) -> dict:
        return FileConfig.CONFIGS.get(file_type)
    
    @staticmethod
    def validate_file_type(file_type: FileType, mime_type: str) -> bool:
        config = FileConfig.get_config(file_type)
        return mime_type in config["allowed_types"]
    
    @staticmethod
    def get_max_size_bytes(file_type: FileType) -> int:
        config = FileConfig.get_config(file_type)
        return config["max_size_mb"] * 1024 * 1024