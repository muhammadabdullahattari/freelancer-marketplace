from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

key = settings.SUPABASE_SERVICE_KEY

print("SERVICE KEY CONFIGURED:", bool(key))
print("SERVICE KEY PREFIX:", key[:10] if key else "EMPTY")

supabase: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_KEY
)

supabase_service: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY
)

def get_supabase_client() -> Client:
    return supabase

def get_supabase_service_client() -> Client:
    return supabase_service