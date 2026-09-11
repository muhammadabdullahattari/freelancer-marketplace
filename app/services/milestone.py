from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.milestone import Milestone, MilestoneStatus
from app.models.contract import Contract, ContractStatus
from uuid import UUID
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


def get_milestone(db: Session, milestone_id: UUID) -> Milestone:
    milestone = db.query(Milestone).filter(Milestone.id == milestone_id).first()
    
    if not milestone:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Milestone not found")
    
    return milestone


def submit_milestone(db: Session,milestone_id: UUID,freelancer_user_id: UUID) -> Milestone:
    
    milestone = get_milestone(db, milestone_id)
    contract = milestone.contract
    
    if contract.freelancer.user_id != freelancer_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to submit this milestone")
    
    if milestone.status not in [MilestoneStatus.PENDING, MilestoneStatus.REJECTED]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only PENDING or REJECTED milestones can be submitted")
    
    try:
        milestone.status = MilestoneStatus.SUBMITTED
        milestone.submitted_at = datetime.now(timezone.utc)
        
        if contract.status == ContractStatus.ACTIVE:
            contract.status = ContractStatus.IN_PROGRESS
        
        db.commit()
        db.refresh(milestone)
        logger.info(f"Milestone submitted: {milestone_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Milestone submission failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to submit milestone")


def approve_milestone(db: Session,milestone_id: UUID,client_user_id: UUID) -> Milestone:
    
    milestone = get_milestone(db, milestone_id)
    contract = milestone.contract
    
    if contract.client_id != client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to approve this milestone")
    
    if milestone.status != MilestoneStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only SUBMITTED milestones can be approved" )
    
    try:
        milestone.status = MilestoneStatus.APPROVED
        milestone.approved_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(milestone)
        logger.info(f"Milestone approved: {milestone_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Milestone approval failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to approve milestone")


def reject_milestone(db: Session,milestone_id: UUID,client_user_id: UUID) -> Milestone:
    
    milestone = get_milestone(db, milestone_id)
    contract = milestone.contract
    
    if contract.client_id != client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to reject this milestone")
    
    if milestone.status != MilestoneStatus.SUBMITTED:
        raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="Only SUBMITTED milestones can be rejected")
    
    try:
        milestone.status = MilestoneStatus.REJECTED
        milestone.rejected_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(milestone)
        logger.info(f"Milestone rejected: {milestone_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Milestone rejection failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to reject milestone")

def release_milestone_payment(db: Session,milestone_id: UUID,client_user_id: UUID) -> Milestone:
    
    milestone = get_milestone(db, milestone_id)
    contract = milestone.contract
    
    if contract.client_id != client_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Not authorized to release payment for this milestone")
    
    if milestone.status != MilestoneStatus.APPROVED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only APPROVED milestones can receive payment")
    
    try:
        milestone.status = MilestoneStatus.PAYMENT_RELEASED
        milestone.payment_released_at = datetime.now(timezone.utc)
        
        contract.amount_paid += milestone.amount
        
        db.commit()
        db.refresh(milestone)
        logger.info(f"Payment released for milestone: {milestone_id}")
        return milestone
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Payment release failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to release payment")
    
def delete_milestone(db: Session, milestone_id: UUID, user_id: UUID) -> None:
    milestone = get_milestone(db, milestone_id)
    contract = milestone.contract
    
    if contract.client_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only client can delete milestones")
    
    if milestone.status != MilestoneStatus.PENDING:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Only PENDING milestones can be deleted")
    
    try:
        db.delete(milestone)
        db.commit()
        logger.info(f"Milestone deleted: {milestone_id}")
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to delete milestone {milestone_id}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to delete milestone")