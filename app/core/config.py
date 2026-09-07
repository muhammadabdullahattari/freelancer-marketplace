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
    model_config = SettingsConfigDict(env_file=".env",extra="ignore")


settings = Settings()