from supabase import create_client, Client
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

logger.info("Supabase service key configured: %s",bool(settings.SUPABASE_SERVICE_KEY))

supabase: Client = create_client(settings.SUPABASE_URL,settings.SUPABASE_KEY)
supabase_service: Client = create_client(settings.SUPABASE_URL,settings.SUPABASE_SERVICE_KEY)

def get_supabase_client() -> Client:
    return supabase

def get_supabase_service_client() -> Client:
    return supabase_service