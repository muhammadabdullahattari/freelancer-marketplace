from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int
    DEBUG: bool
    Test_DATABASE_URL : str
    SUPABASE_URL: str
    SUPABASE_KEY: str 
    SUPABASE_SERVICE_KEY: str  
    SUPABASE_JWT_SECRET: str
    
    MAX_PROFILE_PICTURE_SIZE_MB: int = 5
    MAX_PROPOSAL_ATTACHMENT_SIZE_MB: int = 20
    MAX_CONTRACT_DOCUMENT_SIZE_MB: int = 50
    MAX_MILESTONE_DELIVERABLE_SIZE_MB: int = 100
    
    ALLOWED_IMAGE_TYPES: list[str] = ["image/jpeg", "image/png", "image/webp"]
    ALLOWED_DOCUMENT_TYPES: list[str] = ["application/pdf", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    ALLOWED_FILE_TYPES: list[str] = ["application/pdf", "application/zip", "image/jpeg", "image/png"]
    
    SUPABASE_STORAGE_BUCKET_PROFILES: str = "profile-pictures"
    SUPABASE_STORAGE_BUCKET_PROPOSALS: str = "proposal-attachments"
    SUPABASE_STORAGE_BUCKET_CONTRACTS: str = "contract-documents"
    SUPABASE_STORAGE_BUCKET_MILESTONES: str = "milestone-deliverables"
    
    
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")


settings = Settings()