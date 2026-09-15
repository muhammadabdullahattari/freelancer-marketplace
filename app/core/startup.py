import logging
from app.core.config import settings
from app.core.supabase_client import supabase, supabase_service

logger = logging.getLogger(__name__)


async def verify_supabase_connection():
    try:
        result = supabase.auth.get_session()
        logger.info("Supabase connected successfully")
    except Exception as e:
        logger.error(f"Supabase connection failed: {e}")
        raise


async def verify_and_ensure_storage_buckets():
    """Verify Supabase storage buckets exist, log status, and auto-create if missing"""
    buckets_to_ensure = [
        (settings.SUPABASE_STORAGE_BUCKET_PROFILES.strip("'\" "), True),
        (settings.SUPABASE_STORAGE_BUCKET_PROPOSALS.strip("'\" "), False),
        (settings.SUPABASE_STORAGE_BUCKET_CONTRACTS.strip("'\" "), False),
        (settings.SUPABASE_STORAGE_BUCKET_MILESTONES.strip("'\" "), False),
    ]
    try:
        existing_buckets = supabase_service.storage.list_buckets()
        existing_names = [b.name if hasattr(b, 'name') else b.get('name') for b in existing_buckets] if existing_buckets else []
        logger.info(f"Existing Supabase Storage Buckets: {existing_names}")
        print(f"LIVE SUPABASE BUCKETS: {existing_names}")
        
        for bucket_name, is_public in buckets_to_ensure:
            alt_name = bucket_name.replace("-", "_") if "-" in bucket_name else bucket_name.replace("_", "-")
            if bucket_name not in existing_names and alt_name not in existing_names:
                try:
                    logger.info(f"Bucket '{bucket_name}' not found. Attempting auto-creation...")
                    supabase_service.storage.create_bucket(bucket_name, options={"public": is_public})
                    logger.info(f"Created bucket '{bucket_name}' successfully")
                except Exception as create_err:
                    logger.warning(f"Could not auto-create bucket '{bucket_name}': {create_err}")
    except Exception as e:
        logger.warning(f"Storage bucket verification check failed: {e}")


async def startup_event():
    await verify_supabase_connection()
    await verify_and_ensure_storage_buckets()
