from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session
from app.core.supabase_client import supabase_service
from app.core.file_config import FileConfig, FileType
from app.models.file_upload import FileUpload
from app.core.errors import ValidationException, BusinessLogicException, ErrorCode
from uuid import UUID
import logging
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

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
            filename_without_ext = os.path.splitext(file.filename)[0]
            file_ext = os.path.splitext(file.filename)[1]
            unique_filename = f"{config['folder']}/{timestamp}_{filename_without_ext}_{UUID(int=id(file_content))}{file_ext}"
            
            bucket_name = config["bucket"]
            
            response = supabase_service.storage.from_(bucket_name).upload(
                path=unique_filename,
                file=file_content,
                file_options={"content-type": mime_type}
            )
            
            logger.info(f"File uploaded to Supabase Storage: {bucket_name}/{unique_filename}")
            
            if config["is_public"]:
                storage_url = supabase_service.storage.from_(bucket_name).get_public_url(unique_filename)
            else:
                storage_url = supabase_service.storage.from_(bucket_name).create_signed_url(
                    path=unique_filename,
                    expires_in=7 * 24 * 60 * 60  # 7 days
                )
                storage_url = storage_url["signedURL"] if isinstance(storage_url, dict) else storage_url
            
            file_upload = FileUpload(
                filename=unique_filename,
                original_filename=file.filename,
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
            
            db.add(file_upload)
            db.commit()
            db.refresh(file_upload)
            
            logger.info(f"File record created in DB: {file_upload.id}")
            
            return file_upload
            
        except ValidationException:
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