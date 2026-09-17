from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.models.users import User
from app.services.analytics import AnalyticsService
from app.schemas.analytics import (
    MarketplaceAnalyticsResponse,
    JobAnalyticsResponse,
    ProposalAnalyticsResponse,
    MilestoneAnalyticsResponse,
    FreelancerAnalyticsResponse,
    ClientAnalyticsResponse,
    SkillAnalyticsResponse,
    TrendAnalyticsResponse
)
from datetime import datetime, timedelta, timezone
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

def parse_date(date_str: str) -> datetime:
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt
    except (ValueError, TypeError):
        raise ValueError(f"Invalid date format: {date_str}")

@router.get("/marketplace", response_model=MarketplaceAnalyticsResponse)
async def get_marketplace_analytics(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD")
):

    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Marketplace analytics: {start} to {end}")

    analytics = AnalyticsService.get_marketplace_analytics(db, start, end)
    return analytics

@router.get("/jobs", response_model=JobAnalyticsResponse)
async def get_job_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD")
):
    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Job analytics for user {current_user.id}: {start} to {end}")

    analytics = AnalyticsService.get_job_analytics(db, str(current_user.id), start, end)
    return analytics

@router.get("/proposals", response_model=ProposalAnalyticsResponse)
async def get_proposal_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD")
):
    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Proposal analytics for {current_user.role} {current_user.id}: {start} to {end}")

    analytics = AnalyticsService.get_proposal_analytics(
        db, str(current_user.id), current_user.role, start, end
    )
    return analytics

@router.get("/milestones", response_model=MilestoneAnalyticsResponse)
async def get_milestone_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD")
):
    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Milestone analytics for {current_user.role} {current_user.id}: {start} to {end}")

    analytics = AnalyticsService.get_milestone_analytics(
        db, str(current_user.id), current_user.role, start, end
    )
    return analytics

@router.get("/freelancer/me", response_model=FreelancerAnalyticsResponse)
async def get_freelancer_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    from app.models.freelancer_profile import FreelancerProfile

    logger.info(f"Freelancer analytics for user {current_user.id}")

    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()

    if not freelancer:
        raise ValueError("Freelancer profile not found")

    analytics = AnalyticsService.get_freelancer_analytics(db, str(freelancer.id))
    return analytics

@router.get("/client/me", response_model=ClientAnalyticsResponse)
async def get_client_analytics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    logger.info(f"Client analytics for user {current_user.id}")

    analytics = AnalyticsService.get_client_analytics(db, str(current_user.id))
    return analytics

@router.get("/skills", response_model=SkillAnalyticsResponse)
async def get_skill_analytics(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD"),
    limit: int = Query(50, ge=1, le=100, description="Max skills to return")
):
    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Skill analytics: {start} to {end}")

    analytics = AnalyticsService.get_skill_analytics(db, start, end, limit)
    return analytics

@router.get("/trends", response_model=TrendAnalyticsResponse)
async def get_trend_analytics(
    db: Session = Depends(get_db),
    start_date: str = Query(None, description="Start date YYYY-MM-DD"),
    end_date: str = Query(None, description="End date YYYY-MM-DD"),
    granularity: str = Query("day", pattern="^(day|week|month)$")
):

    end = parse_date(end_date) if end_date else datetime.now(timezone.utc)
    start = parse_date(start_date) if start_date else end - timedelta(days=30)

    logger.info(f"Trend analytics (granularity: {granularity}): {start} to {end}")

    analytics = AnalyticsService.get_trend_analytics(db, start, end, granularity)
    return analytics
