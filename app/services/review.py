from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException, status
from app.models.review import Review
from app.models.contract import Contract, ContractStatus
from app.models.freelancer_profile import FreelancerProfile
from uuid import UUID
from datetime import datetime, timezone
from app.schemas.review import ReviewCreate
import logging

logger = logging.getLogger(__name__)


def create_review(db: Session,contract_id: UUID,reviewer_user_id: UUID,review_data: ReviewCreate) -> Review:
    
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="Contract not found")
    
    if contract.status != ContractStatus.COMPLETED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Can only review completed contracts")
    
    if contract.client_id != reviewer_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,detail="Only contract client can submit reviews")
    
    existing = db.query(Review).filter(Review.contract_id == contract_id,Review.reviewer_id == reviewer_user_id).first()
    
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="You have already reviewed this contract")
    
    rating = review_data.rating
    if not rating or rating < 1 or rating > 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Rating must be between 1 and 5")
    
    try:
        review = Review(
            contract_id=contract_id,
            reviewer_id=reviewer_user_id,
            freelancer_id=contract.freelancer_id,
            rating = review_data.rating,
            title = review_data.title,
            comment = review_data.comment,
            is_anonymous = review_data.is_anonymous
        )
        
        db.add(review)
        db.flush()
        
        update_freelancer_rating(db, contract.freelancer_id)
        
        db.commit()
        db.refresh(review)
        logger.info(f"Review created: {review.id} for contract: {contract_id}")
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