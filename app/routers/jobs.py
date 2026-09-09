from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_client_user
from app.dependencies.pagination import get_pagination_params, PaginationParams, PaginatedResponse
from app.models.users import User
from app.schemas.job import JobCreate, JobUpdate, JobResponse, JobListResponse, JobsListPaginatedResponse
from app.services.job import create_job, get_job, update_job, publish_job, close_job, get_jobs_list, delete_job
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["Jobs"])


@router.post("/", response_model=JobResponse, status_code=201)
def create_job_endpoint(job_data: JobCreate,current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):
    
    request_id = None  
    logger.info(f"Creating job for client: {current_user.id}")
    
    return create_job(db, job_data, current_user.id)

@router.get("/{job_id}", response_model=JobResponse)
def get_job_endpoint(job_id: str,db: Session = Depends(get_db)):
    
    logger.info(f"Fetching job: {job_id}")
    
    return get_job(db, UUID(job_id))


@router.patch("/{job_id}", response_model=JobResponse)
def update_job_endpoint(job_id: str,job_data: JobUpdate,current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):
    logger.info(f"Updating job: {job_id}")
    
    return update_job(db, UUID(job_id), current_user.id, job_data)


@router.post("/{job_id}/publish", response_model=JobResponse)
def publish_job_endpoint(job_id: str,current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):

    logger.info(f"Publishing job: {job_id}")
    
    return publish_job(db, UUID(job_id), current_user.id)

@router.post("/{job_id}/close", response_model=JobResponse)
def close_job_endpoint(job_id: str,current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):
    logger.info(f"Closing job: {job_id}")
    
    return close_job(db, UUID(job_id), current_user.id)

@router.delete("/{job_id}", status_code=204)
def delete_job_endpoint(job_id: str,current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):

    logger.info(f"Deleting job: {job_id}")
    
    delete_job(db, UUID(job_id), current_user.id)


@router.get("/", response_model=JobsListPaginatedResponse)
def list_jobs_endpoint(skip: int = Query(0, ge=0),limit: int = Query(10, ge=1, le=100),status: str = Query(None),search: str = Query(None),
                       client_id: str = Query(None),db: Session = Depends(get_db)):
    
    logger.info(f"Listing jobs - skip: {skip}, limit: {limit}")
    client_uuid = UUID(client_id) if client_id else None
    jobs, total = get_jobs_list(db, skip, limit, status, client_uuid, search)
    
    return {
        "items": [JobListResponse.model_validate(job) for job in jobs],
        "total": total,
        "skip": skip,
        "limit": limit
    }