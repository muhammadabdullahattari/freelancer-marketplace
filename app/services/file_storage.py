import logging
import os
import re
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.errors import BusinessLogicException, ErrorCode, ValidationException
from app.core.file_config import FileConfig, FileType
from app.core.supabase_client import supabase_service
from app.models.file_upload import FileUpload

logger = logging.getLogger(__name__)


def sanitize_filename(filename: str) -> str:
    """Remove special characters and prevent path traversal"""
    # Remove anything that's not alphanumeric, underscore, hyphen, or dot
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Prevent path traversal
    sanitized = sanitized.replace('..', '_').replace('/', '_').replace('\\', '_')
    # Limit length
    return sanitized[:100]


class FileStorageService:
    
    @staticmethod
    async def upload_file(
        file: UploadFile,
        file_type: FileType,
        uploaded_by_user_id: UUID,
        db: Session,
        user_id: UUID | None = None,
        proposal_id: UUID | None = None,
        contract_id: UUID | None = None,
        milestone_id: UUID | None = None
    ) -> FileUpload:
        
        try:
            config = FileConfig.get_config(file_type)
            
            if not config:
                raise ValidationException("Invalid file type")
            
            file_content = await file.read()
            file_size_bytes = len(file_content)
            
            max_size = FileConfig.get_max_size_bytes(file_type)
            if file_size_bytes > max_size:
                raise ValidationException(
                    f"File size {file_size_bytes / 1024 / 1024:.2f}MB exceeds maximum {config['max_size_mb']}MB"
                )
            
            mime_type = file.content_type or "application/octet-stream"
            if not FileConfig.validate_file_type(file_type, mime_type):
                raise ValidationException(
                    f"File type {mime_type} not allowed for {file_type.value}"
                )
            
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            filename_without_ext = os.path.splitext(file.filename)[0] if file.filename else "file"
            file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
            
            safe_filename = sanitize_filename(filename_without_ext)
            unique_filename = f"{config['folder']}/{timestamp}_{safe_filename}_{uuid.uuid4()}{file_ext}"
            
            bucket_name = config["bucket"]
            
            supabase_service.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": mime_type}
            )
            
            logger.info(f"File uploaded to Supabase Storage: {bucket_name}/{unique_filename}")
            
            if config["is_public"]:
                storage_url = supabase_service.storage.from_(bucket_name).get_public_url(unique_filename)
            else:
                storage_url_res = supabase_service.storage.from_(bucket_name).create_signed_url(
                    path=unique_filename,
                    expires_in=7 * 24 * 60 * 60  # 7 days
                )
                storage_url = storage_url_res["signedURL"] if isinstance(storage_url_res, dict) else storage_url_res
            
            file_upload = FileUpload(
                filename=unique_filename,
                original_filename=file.filename or safe_filename,
                file_type=file_type.value,
                mime_type=mime_type,
                file_size_bytes=file_size_bytes,
                storage_bucket=bucket_name,
                storage_path=unique_filename,
                storage_url=storage_url,
                uploaded_by_user_id=uploaded_by_user_id,
                is_public=config["is_public"],
                user_id=user_id,
                proposal_id=proposal_id,
                contract_id=contract_id,
                milestone_id=milestone_id
            )
            
            try:
                db.add(file_upload)
                db.commit()
                db.refresh(file_upload)
                
                logger.info(f"File record created in DB: {file_upload.id}")
                return file_upload
                
            except Exception as db_error:
                db.rollback()
                logger.error(f"DB commit failed: {str(db_error)}, cleaning up storage...")
                try:
                    supabase_service.storage.from_(bucket_name).remove([unique_filename])
                    logger.info(f"Cleaned up orphaned file from storage: {unique_filename}")
                except Exception as cleanup_error:
                    logger.error(f"Failed to cleanup storage file: {str(cleanup_error)}")
                
                raise BusinessLogicException(
                    ErrorCode.INTERNAL_ERROR,
                    f"Failed to save file metadata: {str(db_error)}"
                )
            
        except ValidationException:
            raise
        except BusinessLogicException:
            raise
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                f"Failed to upload file: {str(e)}"
            )
    
    @staticmethod
    def delete_file(file_upload: FileUpload, db: Session) -> None:
        """Delete file from storage and database"""
        
        try:
            bucket_name = file_upload.storage_bucket
            storage_path = file_upload.storage_path
            
            supabase_service.storage.from_(bucket_name).remove([storage_path])
            logger.info(f"File deleted from Supabase Storage: {bucket_name}/{storage_path}")
            
            file_upload.deleted_at = datetime.now(timezone.utc)
            db.commit()
            
            logger.info(f"File record marked as deleted in DB: {file_upload.id}")
            
        except Exception as e:
            logger.error(f"File deletion failed: {str(e)}")
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                f"Failed to delete file: {str(e)}"
            )
    
    @staticmethod
    def get_file_download_url(file_upload: FileUpload, expires_in_seconds: int = 3600) -> str:
        
        if file_upload.is_public:
            return file_upload.storage_url
        
        bucket_name = file_upload.storage_bucket
        storage_path = file_upload.storage_path
        
        try:
            url_response = supabase_service.storage.from_(bucket_name).create_signed_url(
                path=storage_path,
                expires_in=expires_in_seconds
            )
            
            if isinstance(url_response, dict):
                return url_response.get("signedURL", "")
            return url_response
            
        except Exception as e:
            logger.error(f"Failed to generate download URL: {str(e)}")
            raise BusinessLogicException(
                ErrorCode.INTERNAL_ERROR,
                "Failed to generate download URL"
            )
            
    @staticmethod
    def cleanup_resource_files(db: Session, resource_type: str, resource_id: UUID) -> int:
        """Clean up files associated with a resource"""
        try:
            if resource_type == "job":
                files = db.query(FileUpload).filter(FileUpload.job_id == resource_id, FileUpload.deleted_at == None).all()
            elif resource_type == "proposal":
                files = db.query(FileUpload).filter(FileUpload.proposal_id == resource_id, FileUpload.deleted_at == None).all()
            elif resource_type == "contract":
                files = db.query(FileUpload).filter(FileUpload.contract_id == resource_id, FileUpload.deleted_at == None).all()
            elif resource_type == "milestone":
                files = db.query(FileUpload).filter(FileUpload.milestone_id == resource_id, FileUpload.deleted_at == None).all()
            else:
                return 0
            
            deleted_count = 0
            
            for file in files:
                try:
                    supabase_service.storage.from_(file.storage_bucket).remove([file.storage_path])
                    file.deleted_at = datetime.now(timezone.utc)
                    deleted_count += 1
                    logger.info(f"Deleted file {file.id} from {resource_type} {resource_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete file {file.id}: {str(e)}")
                    continue
            
            db.commit()
            logger.info(f"Cleaned up {deleted_count} files for {resource_type} {resource_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Resource file cleanup failed: {str(e)}")
            return 0