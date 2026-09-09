from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.contract import Contract, ContractStatus
from app.models.proposal import Proposal
from app.models.job import Job
from app.models.milestone import Milestone, MilestoneStatus
from uuid import UUID
from datetime import datetime, timezone
from app.schemas.milestone import MilestoneCreate
import logging
from app.models.base import SoftDeleteMixin
from app.core.errors import BusinessLogicException, AuthorizationException,ResourceNotFoundException,ErrorCode

logger = logging.getLogger(__name__)

def create_contract_from_proposal(db: Session, proposal: Proposal) -> Contract:
    
    try:
        contract = Contract(
            job_id=proposal.job_id,
            proposal_id=proposal.id,
            client_id=proposal.job.client_id,
            freelancer_id=proposal.freelancer_id,
            title=proposal.job.title,
            description=proposal.job.description,
            total_amount=proposal.proposed_rate,
            status=ContractStatus.ACTIVE,
            start_date=datetime.now(timezone.utc)
        )
        
        db.add(contract)
        db.flush()
        logger.info(f"Contract created: {contract.id} from proposal: {proposal.id}")
        return contract
        
    except SQLAlchemyError as e:
        logger.error(f"Contract creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to create contract")

def get_contract(db: Session, contract_id: UUID) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at == None).first()
    
    if not contract:
        raise ResourceNotFoundException("Contract")
    
    return contract


def add_milestone(db: Session,contract_id: UUID,user_id: UUID,milestone_data: MilestoneCreate) -> Milestone:
    
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only client can add milestones")
    
    if contract.status not in [ContractStatus.ACTIVE, ContractStatus.IN_PROGRESS]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Contract must be active to add milestones")
    
    try:
        milestone = Milestone(
            contract_id=contract_id,
            title=milestone_data.title,
            description=milestone_data.description,
            amount=milestone_data.amount,
            due_date=milestone_data.due_date,
            order=milestone_data.order)
        
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        logger.info(f"Milestone added: {milestone.id} to contract: {contract_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Milestone creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to add milestone")

def get_contract_milestones(db: Session, contract_id: UUID) -> list[Milestone]:
    contract = get_contract(db, contract_id)
    return db.query(Milestone).filter(Milestone.contract_id == contract_id).order_by(Milestone.order).all()

def complete_contract(db: Session,contract_id: UUID,user_id: UUID) -> Contract:
    
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only client can complete contract")
    
    if contract.status != ContractStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract must be IN_PROGRESS to complete")
    
    pending_milestones = db.query(Milestone).filter(Milestone.contract_id == contract_id,
                        Milestone.status.notin_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED])).first()
    
    if pending_milestones:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="All milestones must be completed before closing contract")
    
    try:
        contract.status = ContractStatus.COMPLETED
        contract.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(contract)
        logger.info(f"Contract completed: {contract_id}")
        return contract
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Contract completion failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to complete contract")


def cancel_contract(db: Session,contract_id: UUID,user_id: UUID) -> Contract:
    
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id and contract.freelancer.user_id != user_id:
        raise AuthorizationException("Not authorized to cancel this contract")
    
    if contract.status == ContractStatus.COMPLETED:
        raise BusinessLogicException(ErrorCode.INVALID_STATE_TRANSITION,"Cannot cancel completed contracts")
        
    try:
        contract.status = ContractStatus.CANCELLED
        contract.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(contract)
        logger.info(f"Contract cancelled: {contract_id}")
        return contract
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Contract cancellation failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR,"Failed to cancel contract")

def get_user_contracts(db: Session,user_id: UUID,role: str, status_filter: str | None = None,skip: int = 0,
                       limit: int = 10) -> tuple[list[Contract], int]:
    
    if role == "CLIENT":
        query = db.query(Contract).filter(Contract.client_id == user_id, Contract.deleted_at == None)
    elif role == "FREELANCER":
        query = db.query(Contract).filter(Contract.freelancer.has(user_id=user_id), Contract.deleted_at == None)
    else:
        raise BusinessLogicException(ErrorCode.INVALID_INPUT,"Invalid role")
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()
    
    return contracts, total