import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import (
    AuthorizationException,
    BusinessLogicException,
    ErrorCode,
    ResourceNotFoundException,
)
from app.models.base import SoftDeleteMixin
from app.models.contract import Contract, ContractStatus
from app.models.job import Job
from app.models.milestone import Milestone, MilestoneStatus
from app.models.proposal import Proposal
from app.schemas.milestone import MilestoneCreate
from app.services.file_storage import FileStorageService

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create contract")


def get_contract(db: Session, contract_id: UUID) -> Contract:
    contract = db.query(Contract).filter(Contract.id == contract_id, Contract.deleted_at == None).first()
    
    if not contract:
        raise ResourceNotFoundException("Contract")
    
    return contract


def add_milestone(db: Session, contract_id: UUID, user_id: UUID, milestone_data: MilestoneCreate) -> Milestone:
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only client can add milestones")
    
    if contract.status not in [ContractStatus.ACTIVE, ContractStatus.IN_PROGRESS]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract must be active to add milestones")
    
    if isinstance(milestone_data, dict):
        m_title = milestone_data.get("title")
        m_description = milestone_data.get("description")
        m_amount = milestone_data.get("amount", 0.0)
        m_due_date = milestone_data.get("due_date")
        m_order = milestone_data.get("order", 1)
    else:
        m_title = milestone_data.title
        m_description = milestone_data.description
        m_amount = milestone_data.amount
        m_due_date = milestone_data.due_date
        m_order = milestone_data.order

    existing_sum = db.query(func.coalesce(func.sum(Milestone.amount), 0.0)).filter(
        Milestone.contract_id == contract_id
    ).scalar() or 0.0

    if float(existing_sum) + float(m_amount) > float(contract.total_amount):
        remaining = max(0.0, float(contract.total_amount) - float(existing_sum))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Milestone amount (${m_amount:.2f}) exceeds remaining contract budget (${remaining:.2f}). Contract total is ${contract.total_amount:.2f}."
        )

    existing_order = db.query(Milestone).filter(
        Milestone.contract_id == contract_id,
        Milestone.order == m_order
    ).first()

    if existing_order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"A milestone with order {m_order} already exists for this contract."
        )

    try:
        milestone = Milestone(
            contract_id=contract_id,
            title=m_title,
            description=m_description,
            amount=m_amount,
            due_date=m_due_date,
            order=m_order
        )
        
        db.add(milestone)
        db.commit()
        db.refresh(milestone)
        logger.info(f"Milestone added: {milestone.id} to contract: {contract_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Milestone creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to add milestone")


def get_contract_milestones(db: Session, contract_id: UUID) -> list[Milestone]:
    contract = get_contract(db, contract_id)
    return db.query(Milestone).filter(Milestone.contract_id == contract_id).order_by(Milestone.order).all()


def complete_contract(db: Session, contract_id: UUID, user_id: UUID) -> Contract:
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only client can complete contract")
    
    if contract.status != ContractStatus.IN_PROGRESS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contract must be IN_PROGRESS to complete")
    
    pending_milestones = db.query(Milestone).filter(
        Milestone.contract_id == contract_id,
        Milestone.status.notin_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED])
    ).first()
    
    if pending_milestones:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All milestones must be completed before closing contract")
    
    unpaid_milestones = db.query(Milestone).filter(
        Milestone.contract_id == contract_id,
        Milestone.status != MilestoneStatus.PAYMENT_RELEASED
    ).first()
    
    if unpaid_milestones:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All milestones must have their payment released before completing the contract.")
    
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to complete contract")


def cancel_contract(db: Session, contract_id: UUID, user_id: UUID) -> Contract:
    contract = get_contract(db, contract_id)
    
    if contract.client_id != user_id and contract.freelancer.user_id != user_id:
        raise AuthorizationException("Not authorized to cancel this contract")
    
    if contract.status == ContractStatus.COMPLETED:
        raise BusinessLogicException(ErrorCode.INVALID_STATE_TRANSITION, "Cannot cancel completed contracts")

    pending_milestone = db.query(Milestone).filter(
        Milestone.contract_id == contract_id,
        Milestone.status == MilestoneStatus.PENDING
    ).first()

    if not pending_milestone:
        raise BusinessLogicException(
            ErrorCode.INVALID_STATE_TRANSITION,
            "Cannot cancel contract: at least one pending milestone is required to cancel this contract."
        )

    active_or_paid_milestones = db.query(Milestone).filter(
        Milestone.contract_id == contract_id,
        Milestone.status.in_([
            MilestoneStatus.SUBMITTED,
            MilestoneStatus.APPROVED,
            MilestoneStatus.PAYMENT_RELEASED
        ])
    ).all()

    if active_or_paid_milestones:
        statuses = {m.status for m in active_or_paid_milestones}
        if MilestoneStatus.PAYMENT_RELEASED in statuses:
            raise BusinessLogicException(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot cancel a contract with released milestone payments."
            )
        else:
            raise BusinessLogicException(
                ErrorCode.INVALID_STATE_TRANSITION,
                "Cannot cancel contract while milestones are submitted or approved. Please resolve active milestones first."
            )
    
    try:
        FileStorageService.cleanup_resource_files(db, "contract", contract_id)
        contract.status = ContractStatus.CANCELLED
        contract.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(contract)
        logger.info(f"Contract cancelled: {contract_id}")
        return contract
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Contract cancellation failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, "Failed to cancel contract")


def get_user_contracts(
    db: Session,
    user_id: UUID,
    role: str,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 10
) -> tuple[list[Contract], int]:
    if role == "CLIENT":
        query = db.query(Contract).filter(Contract.client_id == user_id, Contract.deleted_at == None)
    elif role == "FREELANCER":
        query = db.query(Contract).filter(Contract.freelancer.has(user_id=user_id), Contract.deleted_at == None)
    else:
        raise BusinessLogicException(ErrorCode.INVALID_INPUT, "Invalid role")
    
    if status_filter:
        query = query.filter(Contract.status == status_filter)
    
    total = query.count()
    contracts = query.order_by(Contract.created_at.desc()).offset(skip).limit(limit).all()
    
    return contracts, total