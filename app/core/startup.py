from app.core.supabase_client import supabase
import logging

logger = logging.getLogger(__name__)

async def verify_supabase_connection():
    try:
        result = supabase.auth.get_session()
        logger.info("Supabase connected successfully")
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        raise

async def startup_event():
    await verify_supabase_connection()
