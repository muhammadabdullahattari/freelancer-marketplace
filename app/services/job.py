from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.job import Job, JobStatus
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.models.users import User
from app.schemas.job import JobCreate,JobUpdate
from uuid import UUID
from datetime import datetime, timezone
import logging
from app.services.file_storage import FileStorageService
from app.core.errors import BusinessLogicException, ErrorCode
from app.core.errors import BusinessLogicException, ErrorCode, ResourceNotFoundException, AuthorizationException


logger = logging.getLogger(__name__)


def create_job(db: Session, job_data: JobCreate, client_id: UUID) -> Job:
    try:
        job = Job(
            client_id=client_id,
            title=job_data.title,
            description=job_data.description,
            budget_type=job_data.budget_type,
            budget_min=job_data.budget_min,
            budget_max=job_data.budget_max,
            duration_estimate=job_data.duration_estimate,
            experience_level=job_data.experience_level,
            status=JobStatus.DRAFT,
        )
        
        db.add(job)
        db.flush()
        
        skill_ids = job_data.skill_ids
        if skill_ids:
            for skill_id in skill_ids:
                skill = db.query(Skill).filter(Skill.id == skill_id).first()
                if not skill:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Skill {skill_id} not found")
                
                job_skill = JobSkill(job_id=job.id, skill_id=skill_id)
                db.add(job_skill)
        
        db.commit()
        db.refresh(job)
        logger.info(f"Job created: {job.id} by client: {client_id}")
        return job
        
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Job creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to create job")


def get_job(db: Session, job_id: UUID) -> Job:
    job = db.query(Job).filter(Job.id == job_id , Job.deleted_at == None ).first()
    
    if not job:
        raise ResourceNotFoundException("Job")
    
    return job

def update_job(db: Session, job_id: UUID, client_id: UUID, job_data) -> Job:
    job = get_job(db, job_id)
    
    if job.client_id != client_id:
        raise AuthorizationException("Not authorized to update this job")
    
    if job.status != JobStatus.DRAFT:
        raise BusinessLogicException(ErrorCode.INVALID_STATE_TRANSITION,"Can only update jobs in DRAFT status")
    
    try:
        if hasattr(job_data, 'model_dump'):
            data_dict = job_data.model_dump(exclude_unset=True)
        else:
            data_dict = job_data
        
        for field, value in data_dict.items():
            if field == "skill_ids":
                continue  # Handle separately
            if hasattr(job, field):
                setattr(job, field, value)
        
        if "skill_ids" in data_dict  and data_dict ["skill_ids"] is not None:
            db.query(JobSkill).filter(JobSkill.job_id == job_id).delete()
            for skill_id in data_dict["skill_ids"]:
                skill = db.query(Skill).filter(Skill.id == skill_id).first()
                if not skill:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail=f"Skill {skill_id} not found")
                job_skill = JobSkill(job_id=job_id, skill_id=skill_id)
                db.add(job_skill)
        
        db.commit()
        db.refresh(job)
        logger.info(f"Job updated: {job_id}")
        return job
        
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Job update failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to update job")


def publish_job(db: Session, job_id: UUID, client_id: UUID) -> Job:
    job = get_job(db, job_id)
    
    if job.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to publish this job")
    
    if job.status != JobStatus.DRAFT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only DRAFT jobs can be published")
    
    if not job.title or not job.description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Job must have title and description")
    
    if job.budget_type == "FIXED" and not job.budget_max:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="FIXED budget jobs require budget_max")
    
    try:
        job.status = JobStatus.OPEN
        job.published_at = datetime.now(timezone.utc)
        job.is_active = True
        db.commit()
        db.refresh(job)
        logger.info(f"Job published: {job_id}")
        return job
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Job publish failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to publish job")

def close_job(db: Session, job_id: UUID, client_id: UUID) -> Job:
    job = get_job(db, job_id)
    
    if job.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to close this job")
    
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only OPEN jobs can be closed")
    
    try:
        job.status = JobStatus.CLOSED
        job.closed_at = datetime.now(timezone.utc)
        job.is_active = False
        db.commit()
        db.refresh(job)
        logger.info(f"Job closed: {job_id}")
        return job
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Job close failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to close job")


def get_jobs_list(db: Session, skip: int = 0, limit: int = 10, status_filter: str | None = None, client_id: UUID | None = None, search: str | None = None) -> tuple[list[Job], int]:

    query = db.query(Job).filter(Job.deleted_at == None)
    
    if status_filter:
        query = query.filter(Job.status == status_filter)
    
    if client_id:
        query = query.filter(Job.client_id == client_id)
    
    if search:
        query = query.filter((Job.title.ilike(f"%{search}%")) | (Job.description.ilike(f"%{search}%")))
    
    if not client_id:
        query = query.filter(Job.status == JobStatus.OPEN)
    
    total = query.count()
    query = query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
    jobs = query.all()
    
    return jobs, total
    
async def delete_job(db: Session, job_id: UUID, client_id: UUID) -> None:
    
    job = get_job(db, job_id)
    
    if job.client_id != client_id:
        raise AuthorizationException("Not authorized to delete this job")
    
    if job.status != JobStatus.DRAFT:
        raise BusinessLogicException(ErrorCode.INVALID_STATE_TRANSITION,"Only DRAFT jobs can be deleted")
    
    try:
        await FileStorageService.cleanup_resource_files(db, "job", job_id)
        
        job.deleted_at = datetime.now(timezone.utc)
        db.commit()
        logger.info(f"Job deleted: {job_id}")
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Job deletion failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR,"Failed to delete job")