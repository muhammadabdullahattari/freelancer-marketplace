from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.review import Review
from app.models.contract import Contract, ContractStatus
from app.models.freelancer_profile import FreelancerProfile
from uuid import UUID
from datetime import datetime, timezone
from app.schemas.review import ReviewCreate, ReviewUpdate
import logging

logger = logging.getLogger(__name__)


def create_review(db: Session,contract_id: UUID,reviewer_user_id: UUID,review_data: ReviewCreate) -> Review:
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Contract not found")
    
    if contract.status != ContractStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Can only review completed contracts")
    
    is_client = (contract.client_id == reviewer_user_id)
    is_freelancer = (contract.freelancer and contract.freelancer.user_id == reviewer_user_id)
    
    if not (is_client or is_freelancer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only the client or freelancer assigned to this contract can submit reviews")
    
    existing = db.query(Review).filter(Review.contract_id == contract_id,Review.reviewer_id == reviewer_user_id).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="You have already reviewed this contract")
    
    if isinstance(review_data, dict):
        r_rating = review_data.get("rating")
        r_title = review_data.get("title")
        r_comment = review_data.get("comment")
        r_is_anonymous = review_data.get("is_anonymous", False)
    else:
        r_rating = review_data.rating
        r_title = review_data.title
        r_comment = review_data.comment
        r_is_anonymous = review_data.is_anonymous

    if not r_rating or r_rating < 1 or r_rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")
    
    try:
        review = Review(
            contract_id=contract_id,
            reviewer_id=reviewer_user_id,
            freelancer_id=contract.freelancer_id,
            rating=r_rating,
            title=r_title,
            comment=r_comment,
            is_anonymous=r_is_anonymous
        )
        
        db.add(review)
        db.flush()
        
        if is_client:
            update_freelancer_rating(db, contract.freelancer_id)
        
        db.commit()
        db.refresh(review)
        logger.info(f"Review created: {review.id} for contract: {contract_id}")

        # Queue notification to freelancer about review
        try:
            from app.services.notification import NotificationService
            from app.models.notifications import NotificationEventType
            from app.models.users import User
            
            reviewer = db.query(User).filter(User.id == review.reviewer_id).first()
            reviewer_name = reviewer.name if reviewer else "A user"
            freelancer_user_id = contract.freelancer.user_id if contract.freelancer else None
            
            if freelancer_user_id:
                NotificationService.queue_notification(
                    db=db,
                    event_type=NotificationEventType.REVIEW_SUBMITTED.value,
                    recipient_user_id=freelancer_user_id,
                    email_subject=f"You've Received a Review from {reviewer_name}",
                    email_body_html=f"""
                        <html><body>
                            <h2>New Review Received!</h2>
                            <p>You received a new {review.rating}-star review from {reviewer_name}.</p>
                        </body></html>
                    """,
                    resource_type="review",
                    resource_id=review.id,
                    triggered_by_user_id=review.reviewer_id,
                    event_payload={"rating": review.rating, "reviewer_name": reviewer_name}
                )
        except Exception as e:
            logger.error(f"Failed to queue review notification: {str(e)}")

        return review
        
    except HTTPException:
        db.rollback()
        raise
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Review creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="Failed to create review")


def get_review(db: Session, review_id: UUID) -> Review:
    review = db.query(Review).filter(Review.id == review_id).first()
    
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Review not found")
    
    return review


def update_review(db: Session, review_id: UUID, user_id: UUID, update_data: ReviewUpdate) -> Review:
    review = get_review(db, review_id)
    
    if review.reviewer_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the author of this review can update it"
        )
    
    if isinstance(update_data, dict):
        new_rating = update_data.get("rating")
        new_title = update_data.get("title")
        new_comment = update_data.get("comment")
    else:
        new_rating = update_data.rating
        new_title = update_data.title
        new_comment = update_data.comment
    
    if new_rating is not None:
        if new_rating < 1 or new_rating > 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rating must be between 1 and 5"
            )
        review.rating = new_rating
        
    if new_title is not None:
        review.title = new_title
        
    if new_comment is not None:
        review.comment = new_comment
        
    review.updated_at = datetime.now(timezone.utc)
    
    try:
        db.commit()
        db.refresh(review)
        
        if review.contract and review.contract.client_id == user_id:
            update_freelancer_rating(db, review.freelancer_id)
            
        logger.info(f"Review updated: {review_id}")
        return review
    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to update review {review_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update review"
        )


def get_freelancer_reviews(db: Session,freelancer_id: UUID,skip: int = 0,limit: int = 10) -> tuple[list[Review], int]:
    
    query = db.query(Review).filter(Review.freelancer_id == freelancer_id)
    total = query.count()
    reviews = query.order_by(Review.created_at.desc()).offset(skip).limit(limit).all()
    
    return reviews, total


def get_contract_reviews(db: Session, contract_id: UUID) -> list[Review]:
    return db.query(Review).filter(Review.contract_id == contract_id).all()


def update_freelancer_rating(db: Session, freelancer_id: UUID) -> None:
    
    freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.id == freelancer_id).first()
    
    if not freelancer:
        return
    
    reviews = db.query(Review).filter(Review.freelancer_id == freelancer_id).all()
    
    if reviews:
        avg_rating = sum(r.rating for r in reviews) / len(reviews)
        freelancer.average_rating = round(avg_rating, 2)
        freelancer.total_reviews = len(reviews)
    else:
        freelancer.average_rating = None
        freelancer.total_reviews = 0