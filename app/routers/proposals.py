from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user, get_current_freelancer_user, get_current_client_user
from app.models.users import User
from app.schemas.proposal import ProposalCreate, ProposalResponse, ProposalsListPaginatedResponse
from app.services.proposal import (
    submit_proposal, get_proposal, accept_proposal, reject_proposal,
    get_job_proposals, get_freelancer_proposals, withdraw_proposal
)
import logging
from uuid import UUID
from app.models.freelancer_profile import FreelancerProfile
from app.core.errors import ResourceNotFoundException


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/proposals", tags=["Proposals"])


@router.post("/", response_model=ProposalResponse, status_code=201)
async def submit_proposal_endpoint(job_id: str,proposal_data: ProposalCreate,current_user: User = Depends(get_current_freelancer_user),
                                   db: Session = Depends(get_db)):
    
    logger.info(f"Freelancer {current_user.id} submitting proposal for job {job_id}")
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id).first()
    
    if not freelancer:
        raise ResourceNotFoundException("Freelancer profile")
    
    return submit_proposal(db, UUID(job_id), freelancer.id, proposal_data.model_dump())


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal_endpoint(proposal_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching proposal: {proposal_id}")
    
    return get_proposal(db, UUID(proposal_id))


@router.post("/{proposal_id}/accept", response_model=ProposalResponse)
async def accept_proposal_endpoint(proposal_id: str,current_user: User = Depends(get_current_client_user),
                                   db: Session = Depends(get_db)):
    
    logger.info(f"Client {current_user.id} accepting proposal {proposal_id}")
    
    return accept_proposal(db, UUID(proposal_id), current_user.id)

@router.post("/{proposal_id}/reject", response_model=ProposalResponse)
async def reject_proposal_endpoint(proposal_id: str,current_user: User = Depends(get_current_client_user),
                                   db: Session = Depends(get_db)):
    
    logger.info(f"Client {current_user.id} rejecting proposal {proposal_id}")
    
    return reject_proposal(db, UUID(proposal_id), current_user.id)


@router.post("/{proposal_id}/withdraw", status_code=204)
async def withdraw_proposal_endpoint(proposal_id: str,current_user: User = Depends(get_current_freelancer_user),
                                     db: Session = Depends(get_db)):
    
    logger.info(f"Freelancer {current_user.id} withdrawing proposal {proposal_id}")
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id).first()
    
    if not freelancer:
        raise ResourceNotFoundException("Freelancer profile")
    
    withdraw_proposal(db, UUID(proposal_id), freelancer.id)


@router.get("/job/{job_id}", response_model=ProposalsListPaginatedResponse)
async def get_job_proposals_endpoint(job_id: str,skip: int = Query(0, ge=0),limit: int = Query(10, ge=1, le=100),
    status: str = Query(None),current_user: User = Depends(get_current_client_user),db: Session = Depends(get_db)):
    
    logger.info(f"Listing proposals for job {job_id}")
    proposals, total = get_job_proposals(db, UUID(job_id), current_user.id, status, skip, limit)
    
    return {
        "items": [ProposalResponse.model_validate(p) for p in proposals],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/me/submitted", response_model=ProposalsListPaginatedResponse)
async def get_my_proposals_endpoint(skip: int = Query(0, ge=0),limit: int = Query(10, ge=1, le=100),
                                    status: str = Query(None),current_user: User = Depends(get_current_freelancer_user),db: Session = Depends(get_db)):
    
    logger.info(f"Listing proposals by freelancer {current_user.id}")
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id).first()
    
    if not freelancer:
        raise ResourceNotFoundException("Freelancer profile")
    
    proposals, total = get_freelancer_proposals(db, freelancer.id, status, skip, limit)
    
    return {
        "items": [ProposalResponse.model_validate(p) for p in proposals],
        "total": total,
        "skip": skip,
        "limit": limit
    }