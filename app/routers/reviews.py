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
router = APIRouter(prefix="/reviews", tags=["Reviews"])


@router.post("/", response_model=ReviewResponse, status_code=201)
def create_review_endpoint(contract_id: str,review_data: ReviewCreate,current_user: User = Depends(get_current_user),
                                 db: Session = Depends(get_db)):
    
    logger.info(f"User {current_user.id} creating review for contract {contract_id}")
    return create_review(db, UUID(contract_id), current_user.id, review_data)


@router.get("/contract/{contract_id}", response_model=list[ReviewResponse])
def get_contract_reviews_endpoint(contract_id: str,db: Session = Depends(get_db)):
    logger.info(f"Fetching reviews for contract {contract_id}")    
    return get_contract_reviews(db, UUID(contract_id))