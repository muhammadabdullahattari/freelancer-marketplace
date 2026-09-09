from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.schemas.review import ReviewCreate, ReviewResponse, ReviewsListPaginatedResponse
from app.services.review import (
    create_review, get_review, get_freelancer_reviews, get_contract_reviews
)
import logging
from uuid import UUID

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=201)
async def create_review_endpoint(contract_id: str,review_data: ReviewCreate,current_user: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    
    logger.info(f"User {current_user.id} creating review for contract {contract_id}")
    return create_review(db, UUID(contract_id), current_user.id, review_data.model_dump())

@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review_endpoint(review_id: str,db: Session = Depends(get_db)):
    
    logger.info(f"Fetching review: {review_id}")
    return get_review(db, UUID(review_id))

@router.get("/freelancer/{freelancer_id}", response_model=ReviewsListPaginatedResponse)
async def get_freelancer_reviews_endpoint(freelancer_id: str,skip: int = Query(0, ge=0),
                                          limit: int = Query(10, ge=1, le=100),db: Session = Depends(get_db)):
    
    logger.info(f"Fetching reviews for freelancer {freelancer_id}")
    reviews, total = get_freelancer_reviews(db, UUID(freelancer_id), skip, limit)
    
    return {
        "items": [ReviewResponse.model_validate(r) for r in reviews],
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/contract/{contract_id}", response_model=list[ReviewResponse])
async def get_contract_reviews_endpoint(contract_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching reviews for contract {contract_id}")    
    return get_contract_reviews(db, UUID(contract_id))