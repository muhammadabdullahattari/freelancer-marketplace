import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.errors import (
    AuthorizationException,
    BusinessLogicException,
    ConflictException,
    ErrorCode,
    ResourceNotFoundException,
)
from app.models.base import SoftDeleteMixin
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus
from app.schemas.proposal import ProposalCreate
from app.services.contract import create_contract_from_proposal
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)


def submit_proposal(db: Session, job_id: UUID, freelancer_id: UUID, proposal_data: ProposalCreate) -> Proposal:
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise ResourceNotFoundException("Job")
    
    if job.status != JobStatus.OPEN:
        raise BusinessLogicException(ErrorCode.JOB_NOT_OPEN, "Job is not accepting proposals")
    
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.id == freelancer_id).first()
    
    if not freelancer:
        raise ResourceNotFoundException("Freelancer profile")
    
    if job.client_id == freelancer.user_id:
        raise BusinessLogicException(ErrorCode.INVALID_OPERATION, "Cannot submit proposal to your own job")
    
    existing = db.query(Proposal).filter(
        Proposal.job_id == job_id,
        Proposal.freelancer_id == freelancer_id,
        Proposal.status.in_([ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW])
    ).first()
    
    if existing:
        raise ConflictException("You have already submitted a proposal for this job")
    
    try:
        proposal = Proposal(
            job_id=job_id,
            freelancer_id=freelancer_id,
            cover_letter=proposal_data.cover_letter,
            proposed_rate=proposal_data.proposed_rate,
            estimated_duration=proposal_data.estimated_duration,
            status=ProposalStatus.SUBMITTED
        )
        
        db.add(proposal)
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal submitted: {proposal.id} by freelancer: {freelancer_id}")

        # Queue notification to job client
        try:
            from app.services.notification import NotificationService
            from app.models.notifications import NotificationEventType
            from app.models.users import User
            
            client_user = db.query(User).filter(User.id == job.client_id).first()
            freelancer_user = db.query(User).filter(User.id == freelancer.user_id).first()
            client_name = client_user.name if client_user else "Client"
            freelancer_name = freelancer_user.name if freelancer_user else "Freelancer"
            
            NotificationService.queue_notification(
                db=db,
                event_type=NotificationEventType.PROPOSAL_RECEIVED.value,
                recipient_user_id=job.client_id,
                email_subject=f"New Proposal for Your Job: {job.title}",
                email_body_html=f"""
                    <html><body>
                        <h2>New Proposal Received!</h2>
                        <p>Hi {client_name},</p>
                        <p>You have a new proposal from {freelancer_name}</p>
                        <p>Proposed Rate: ${proposal.proposed_rate}/hour</p>
                    </body></html>
                """,
                resource_type="proposal",
                resource_id=proposal.id,
                triggered_by_user_id=freelancer.user_id,
                event_payload={
                    "job_title": job.title,
                    "job_id": str(job.id),
                    "freelancer_name": freelancer_name,
                    "proposed_rate": proposal.proposed_rate
                }
            )
        except Exception as e:
            logger.error(f"Failed to queue proposal notification: {str(e)}")

        return proposal
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Proposal submission failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, "Failed to submit proposal")


def get_proposal(db: Session, proposal_id: UUID) -> Proposal:
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id, Proposal.deleted_at == None).first()
    
    if not proposal:
        raise ResourceNotFoundException("Proposal")
    
    return proposal


def accept_proposal(db: Session, proposal_id: UUID, client_id: UUID) -> Proposal:
    proposal = get_proposal(db, proposal_id)
    job = proposal.job
    
    if job.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to accept this proposal")
    
    if job.status != JobStatus.OPEN:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Job is not accepting proposals")
    
    if proposal.status != ProposalStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only SUBMITTED proposals can be accepted")
    
    accepted = db.query(Proposal).filter(Proposal.job_id == proposal.job_id, Proposal.status == ProposalStatus.ACCEPTED).first()
    
    if accepted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A proposal has already been accepted for this job")
    
    try:
        proposal.status = ProposalStatus.ACCEPTED
        proposal.accepted_at = datetime.now(timezone.utc)
        
        other_proposals = db.query(Proposal).filter(
            Proposal.job_id == proposal.job_id,
            Proposal.id != proposal_id, 
            Proposal.status == ProposalStatus.SUBMITTED
        ).all()
        
        for other in other_proposals:
            other.status = ProposalStatus.REJECTED
            other.rejected_at = datetime.now(timezone.utc)
        
        db.flush()
        contract = create_contract_from_proposal(db, proposal)
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal accepted: {proposal_id}, contract created: {contract.id}")

        # Queue acceptance notification to freelancer
        try:
            from app.services.notification import NotificationService
            from app.models.notifications import NotificationEventType
            from app.models.users import User
            
            freelancer_user = db.query(User).filter(User.id == proposal.freelancer.user_id).first()
            client = db.query(User).filter(User.id == job.client_id).first()
            freelancer_name = freelancer_user.name if freelancer_user else "Freelancer"
            client_name = client.name if client else "Client"
            
            NotificationService.queue_notification(
                db=db,
                event_type=NotificationEventType.PROPOSAL_ACCEPTED.value,
                recipient_user_id=proposal.freelancer.user_id,
                email_subject="Your Proposal Was Accepted! 🎉",
                email_body_html=f"""
                    <html><body>
                        <h2>Congratulations!</h2>
                        <p>Hi {freelancer_name},</p>
                        <p>{client_name} has accepted your proposal for: {job.title}</p>
                        <p>Rate: ${proposal.proposed_rate}/hour</p>
                    </body></html>
                """,
                resource_type="proposal",
                resource_id=proposal.id,
                triggered_by_user_id=job.client_id,
                event_payload={"job_title": job.title, "client_name": client_name}
            )
        except Exception as e:
            logger.error(f"Failed to queue acceptance notification: {str(e)}")

        return proposal
        
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Proposal acceptance failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to accept proposal")


def reject_proposal(db: Session, proposal_id: UUID, client_id: UUID) -> Proposal:
    proposal = get_proposal(db, proposal_id)
    job = proposal.job
    
    if job.client_id != client_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to reject this proposal")
    
    if proposal.status != ProposalStatus.SUBMITTED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only SUBMITTED proposals can be rejected")
    
    try:
        proposal.status = ProposalStatus.REJECTED
        proposal.rejected_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal rejected: {proposal_id}")
        return proposal
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Proposal rejection failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to reject proposal")


def get_job_proposals(
    db: Session,
    job_id: UUID,
    client_id: UUID,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 10
) -> tuple[list[Proposal], int]:
    job = db.query(Job).filter(Job.id == job_id, Job.deleted_at == None).first()
    if not job:
        raise ResourceNotFoundException("Job")
    
    if job.client_id != client_id:
        raise AuthorizationException("Not authorized to view proposals for this job")
    
    query = db.query(Proposal).filter(Proposal.job_id == job_id, Proposal.deleted_at == None)
    
    if status_filter:
        query = query.filter(Proposal.status == status_filter)
    
    total = query.count()
    proposals = query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit).all()
    
    return proposals, total


def get_freelancer_proposals(
    db: Session,
    freelancer_id: UUID,
    status_filter: str | None = None,
    skip: int = 0,
    limit: int = 10
) -> tuple[list[Proposal], int]:
    query = db.query(Proposal).filter(Proposal.freelancer_id == freelancer_id, Proposal.deleted_at == None)
    
    if status_filter:
        query = query.filter(Proposal.status == status_filter)
    
    total = query.count()
    proposals = query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit).all()
    
    return proposals, total


def withdraw_proposal(db: Session, proposal_id: UUID, freelancer_id: UUID) -> Proposal:
    proposal = get_proposal(db, proposal_id)
    
    if proposal.freelancer_id != freelancer_id:
        raise AuthorizationException("Not authorized to withdraw this proposal")
    
    if proposal.status not in [ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW]:
        raise BusinessLogicException(ErrorCode.INVALID_STATE_TRANSITION, "Only SUBMITTED or UNDER_REVIEW proposals can be withdrawn")
    
    try:
        FileStorageService.cleanup_resource_files(db, "proposal", proposal_id)
        proposal.status = ProposalStatus.WITHDRAWN
        proposal.deleted_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(proposal)
        logger.info(f"Proposal withdrawn: {proposal_id}")
        return proposal
        
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Proposal withdrawal failed: {str(e)}")
        raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, "Failed to withdraw proposal")