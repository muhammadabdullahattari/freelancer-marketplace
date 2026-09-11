from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.schemas.milestone import MilestoneResponse
from app.services.milestone import (
    get_milestone, submit_milestone, approve_milestone,
    reject_milestone, release_milestone_payment, delete_milestone
)
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/milestones", tags=["Milestones"])


@router.get("/{milestone_id}", response_model=MilestoneResponse)
def get_milestone_endpoint(milestone_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching milestone: {milestone_id}")    
    return get_milestone(db, UUID(milestone_id))

@router.post("/{milestone_id}/submit", response_model=MilestoneResponse)
def submit_milestone_endpoint(milestone_id: str,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Submitting milestone {milestone_id}")
    return submit_milestone(db, UUID(milestone_id), current_user.id)

@router.post("/{milestone_id}/approve", response_model=MilestoneResponse)
def approve_milestone_endpoint(milestone_id: str,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Approving milestone {milestone_id}")
    return approve_milestone(db, UUID(milestone_id), current_user.id)

@router.post("/{milestone_id}/reject", response_model=MilestoneResponse)
def reject_milestone_endpoint(milestone_id: str,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Rejecting milestone {milestone_id}")
    return reject_milestone(db, UUID(milestone_id), current_user.id)

@router.post("/{milestone_id}/release-payment", response_model=MilestoneResponse)
def release_payment_endpoint(milestone_id: str,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Releasing payment for milestone {milestone_id}")
    return release_milestone_payment(db, UUID(milestone_id), current_user.id)

@router.delete("/{milestone_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_milestone_endpoint(milestone_id: str,current_user: User = Depends(get_current_user),db: Session = Depends(get_db)):
    logger.info(f"Deleting milestone: {milestone_id}")
    delete_milestone(db, UUID(milestone_id), current_user.id)
    return None