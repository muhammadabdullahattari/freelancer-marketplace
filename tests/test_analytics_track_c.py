import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.models.users import User
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.contract import Contract, ContractStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.freelancer_profile import FreelancerProfile
from app.models.review import Review
from app.models.skill import Skill
from app.models.job_skill import JobSkill

from app.services.analytics import AnalyticsService
from app.core.errors import AuthorizationException, BusinessLogicException

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

# ============================================================================
# 1. ZERO DIVISION & EMPTY DATA TESTS
# ============================================================================

def test_marketplace_analytics_zero_division(db_session: Session):
    """Verify get_marketplace_analytics handles zero data without DivisionByZero errors."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    data = AnalyticsService.get_marketplace_analytics(db_session, start, now)
    
    assert data["jobs"]["created"] == 0
    assert data["jobs"]["published"] == 0
    assert data["jobs"]["completed"] == 0
    assert data["jobs"]["completion_rate"] == 0.0
    
    assert data["proposals"]["submitted"] == 0
    assert data["proposals"]["accepted"] == 0
    assert data["proposals"]["acceptance_rate"] == 0.0
    
    assert data["contracts"]["created"] == 0
    assert data["contracts"]["completed"] == 0
    assert data["contracts"]["total_value"] == 0.0
    
    # Validate against Pydantic schema
    response_schema = MarketplaceAnalyticsResponse(**data)
    assert response_schema.jobs.completion_rate == 0.0


def test_job_analytics_zero_division(db_session: Session, client_user: User):
    """Verify get_job_analytics handles zero published jobs safely."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    data = AnalyticsService.get_job_analytics(db_session, str(client_user.id), start, now)
    assert data["jobs"]["completion_rate"] == 0.0
    assert data["jobs"]["avg_proposals_per_job"] == 0.0
    
    response_schema = JobAnalyticsResponse(**data)
    assert response_schema.client_id == str(client_user.id)


def test_proposal_analytics_zero_division_client(db_session: Session, client_user: User):
    """Verify get_proposal_analytics handles zero proposals safely for client."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    data = AnalyticsService.get_proposal_analytics(db_session, str(client_user.id), "CLIENT", start, now)
    assert data["funnel"]["submitted"] == 0
    assert data["funnel"]["acceptance_rate"] == 0.0
    assert data["funnel"]["rejection_rate"] == 0.0
    
    response_schema = ProposalAnalyticsResponse(**data)
    assert response_schema.role == "CLIENT"


def test_milestone_analytics_zero_division(db_session: Session, client_user: User):
    """Verify get_milestone_analytics handles zero milestones safely."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    data = AnalyticsService.get_milestone_analytics(db_session, str(client_user.id), "CLIENT", start, now)
    assert data["milestones"]["approval_rate"] == 0.0
    assert data["milestones"]["rejection_rate"] == 0.0
    assert data["milestones"]["overdue"] == 0
    
    response_schema = MilestoneAnalyticsResponse(**data)
    assert response_schema.milestones.approval_rate == 0.0


# ============================================================================
# 2. ROLE-BASED DATA ISOLATION TESTS
# ============================================================================

def test_role_authorization_check(db_session: Session, freelancer_user: User):
    """Verify non-clients get exception when requesting job analytics."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    with pytest.raises((AuthorizationException, BusinessLogicException)) as exc_info:
        AnalyticsService.get_job_analytics(db_session, str(freelancer_user.id), start, now)
    assert "Only clients can view job analytics" in str(exc_info.value)


def test_proposal_analytics_isolation(db_session: Session, client_user: User, freelancer_user: User):
    """Verify proposals are isolated: Client sees client's jobs proposals, Freelancer sees freelancer's proposals."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    
    fp = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title="Dev", hourly_rate=50.0)
    db_session.add(fp)
    
    job = Job(
        id=uuid.uuid4(),
        client_id=client_user.id,
        title="Test Job",
        description="Detailed description for test job",
        status=JobStatus.OPEN,
        created_at=now
    )
    db_session.add(job)
    db_session.commit()
    
    prop = Proposal(
        id=uuid.uuid4(),
        job_id=job.id,
        freelancer_id=fp.id,
        status=ProposalStatus.SUBMITTED,
        cover_letter="Interested",
        proposed_rate=50.0,
        created_at=now
    )
    db_session.add(prop)
    db_session.commit()
    
    client_data = AnalyticsService.get_proposal_analytics(db_session, str(client_user.id), "CLIENT", start, now + timedelta(days=1))
    assert client_data["funnel"]["submitted"] == 1
    
    freelancer_data = AnalyticsService.get_proposal_analytics(db_session, str(freelancer_user.id), "FREELANCER", start, now + timedelta(days=1))
    assert freelancer_data["funnel"]["submitted"] == 1
    
    other_client = User(id=uuid.uuid4(), username="client2", name="Client Two", email="client2@test.com", role="CLIENT")
    db_session.add(other_client)
    db_session.commit()
    
    other_data = AnalyticsService.get_proposal_analytics(db_session, str(other_client.id), "CLIENT", start, now + timedelta(days=1))
    assert other_data["funnel"]["submitted"] == 0


def test_freelancer_performance_metrics(db_session: Session, freelancer_user: User):
    """Verify get_freelancer_analytics aggregates performance metrics correctly."""
    fp = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title="Senior Dev", hourly_rate=75.0)
    db_session.add(fp)
    db_session.commit()
    
    data = AnalyticsService.get_freelancer_analytics(db_session, str(fp.id))
    assert data["freelancer_id"] == str(fp.id)
    assert data["performance"]["proposals_submitted"] == 0
    assert data["performance"]["total_earnings"] == 0.0
    
    response_schema = FreelancerAnalyticsResponse(**data)
    assert response_schema.performance.success_rate == 0.0


def test_client_activity_metrics(db_session: Session, client_user: User):
    """Verify get_client_analytics aggregates client activity correctly."""
    data = AnalyticsService.get_client_analytics(db_session, str(client_user.id))
    assert data["client_id"] == str(client_user.id)
    assert data["activity"]["total_jobs_posted"] == 0
    assert data["activity"]["total_spent"] == 0.0
    
    response_schema = ClientAnalyticsResponse(**data)
    assert response_schema.activity.total_jobs_posted == 0


def test_api_analytics_router_registration(client: TestClient):
    """
    Test GET /api/analytics/marketplace endpoint natively included in main app.
    """
    res = client.get("/api/analytics/marketplace")
    assert res.status_code == 200
    res_data = res.json()
    assert "jobs" in res_data
    assert "completion_rate" in res_data["jobs"]


def test_skill_analytics_success_rate_boundary(db_session: Session, client_user: User, freelancer_user: User):
    """Verify get_skill_analytics success_rate does not exceed 100.0 when multiple proposals exist for a job."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)

    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Python Dev Required", description="Test desc", budget_min=500.0, status=JobStatus.OPEN, created_at=now)
    db_session.add(job)

    skill = Skill(id=uuid.uuid4(), name="Python_Testing_Boundary_Skill")
    db_session.add(skill)

    job_skill = JobSkill(job_id=job.id, skill_id=skill.id)
    db_session.add(job_skill)

    prop1 = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_user.id, cover_letter="Cover letter 1", proposed_rate=50.0, status=ProposalStatus.ACCEPTED, created_at=now)
    other_freelancer = User(id=uuid.uuid4(), username="free2", name="Free Two", email="free2@test.com", role="FREELANCER")
    db_session.add(other_freelancer)
    prop2 = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=other_freelancer.id, cover_letter="Cover letter 2", proposed_rate=60.0, status=ProposalStatus.SUBMITTED, created_at=now)
    db_session.add_all([prop1, prop2])
    db_session.commit()

    data = AnalyticsService.get_skill_analytics(db_session, start, now + timedelta(days=1))
    target_skill = next((s for s in data["skills"] if s["skill_id"] == str(skill.id)), None)
    assert target_skill is not None
    assert target_skill["success_rate"] <= 100.0
    assert target_skill["success_rate"] == 50.0

    response_schema = SkillAnalyticsResponse(**data)
    assert response_schema.skills[0].success_rate <= 100.0


def test_payment_released_milestones_analytics(db_session: Session, client_user: User, freelancer_user: User):
    """Verify PAYMENT_RELEASED milestones count as approved/submitted and are NOT marked overdue."""
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=30)
    past_due = now - timedelta(days=2)

    fp = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title="Senior Dev", hourly_rate=75.0)
    db_session.add(fp)

    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Backend Dev", description="Desc", status=JobStatus.CLOSED)
    db_session.add(job)

    prop = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_user.id, cover_letter="Cover", proposed_rate=100.0, status=ProposalStatus.ACCEPTED)
    db_session.add(prop)

    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=prop.id, client_id=client_user.id, freelancer_id=fp.id, title="Contract 1", total_amount=1000.0, status=ContractStatus.COMPLETED)
    db_session.add(contract)

    m1 = Milestone(
        id=uuid.uuid4(),
        contract_id=contract.id,
        title="M1",
        amount=500.0,
        status=MilestoneStatus.PAYMENT_RELEASED,
        due_date=past_due,
        submitted_at=now - timedelta(days=5),
        approved_at=now - timedelta(days=4),
        payment_released_at=now - timedelta(days=4)
    )
    db_session.add(m1)
    db_session.commit()

    data = AnalyticsService.get_milestone_analytics(db_session, str(freelancer_user.id), "FREELANCER", start, now + timedelta(days=1))
    
    assert data["milestones"]["submitted"] == 1
    assert data["milestones"]["approved"] == 1
    assert data["milestones"]["overdue"] == 0
    assert data["milestones"]["approval_rate"] == 100.0
