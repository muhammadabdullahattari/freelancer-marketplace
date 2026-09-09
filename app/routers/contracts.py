from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.schemas.contract import ContractResponse, ContractListResponse, ContractsListPaginatedResponse
from app.schemas.milestone import MilestoneCreate, MilestoneResponse
from app.services.contract import (
    get_contract, add_milestone, get_contract_milestones,
    complete_contract, cancel_contract, get_user_contracts
)
import logging
from uuid import UUID
from app.models.freelancer_profile import FreelancerProfile


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/contracts", tags=["Contracts"])


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract_endpoint(contract_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching contract: {contract_id}")
    
    return get_contract(db, UUID(contract_id))


@router.post("/{contract_id}/milestones", response_model=MilestoneResponse, status_code=201)
async def add_milestone_endpoint(contract_id: str,milestone_data: MilestoneCreate,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Adding milestone to contract {contract_id}")
    
    return add_milestone(db, UUID(contract_id), current_user.id, milestone_data.model_dump())


@router.get("/{contract_id}/milestones", response_model=list[MilestoneResponse])
async def get_contract_milestones_endpoint(contract_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching milestones for contract {contract_id}")
    
    return get_contract_milestones(db, UUID(contract_id))

@router.post("/{contract_id}/complete", response_model=ContractResponse)
async def complete_contract_endpoint(contract_id: str,current_user: User = Depends(get_current_user),
                                     db: Session = Depends(get_db)):
    logger.info(f"Completing contract {contract_id}")
    
    return complete_contract(db, UUID(contract_id), current_user.id)


@router.post("/{contract_id}/cancel", status_code=204)
async def cancel_contract_endpoint(contract_id: str,current_user: User = Depends(get_current_user),
                                   db: Session = Depends(get_db)):
    
    logger.info(f"Cancelling contract {contract_id}")
    cancel_contract(db, UUID(contract_id), current_user.id)


@router.get("/", response_model=ContractsListPaginatedResponse)
async def list_contracts_endpoint(skip: int = Query(0, ge=0),limit: int = Query(10, ge=1, le=100),status: str = Query(None),
                                  current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    
    logger.info(f"Listing contracts for user {current_user.id}")
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id).first()
    
    if freelancer:
        contracts, total = get_user_contracts(db, freelancer.id, "FREELANCER", status, skip, limit)
    else:
        contracts, total = get_user_contracts(db, current_user.id, "CLIENT", status, skip, limit)
    
    return {
        "items": [ContractListResponse.model_validate(c) for c in contracts],
        "total": total,
        "skip": skip,
        "limit": limit
    }