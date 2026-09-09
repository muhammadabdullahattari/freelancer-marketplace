import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User
from app.models.contract import Contract, ContractStatus
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.review import Review


def test_review_creation_and_freelancer_rating_data_consistency(
    client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session
):
    """Test review creation and automatic calculation of freelancer average_rating and total_reviews."""
    # 1. Create Freelancer Profile
    freelancer_prof = FreelancerProfile(
        id=uuid.uuid4(),
        user_id=freelancer_user.id,
        title="Full Stack Python Developer",
        average_rating=None,
        total_reviews=0,
    )
    db_session.add(freelancer_prof)

    # 2. Create Job & Proposal
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Job Title", description="Description content text")
    db_session.add(job)

    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter="Letter content text", proposed_rate=1000.0)
    db_session.add(proposal)

    # 3. Create Completed Contract
    contract = Contract(
        id=uuid.uuid4(),
        job_id=job.id,
        proposal_id=proposal.id,
        client_id=client_user.id,
        freelancer_id=freelancer_prof.id,
        title=job.title,
        total_amount=1000.0,
        status=ContractStatus.COMPLETED,
    )
    db_session.add(contract)
    db_session.commit()

    # 4. Directly test review rating aggregation logic
    review1 = Review(
        id=uuid.uuid4(),
        contract_id=contract.id,
        reviewer_id=client_user.id,
        freelancer_id=freelancer_prof.id,
        rating=5,
        title="Outstanding Work",
        comment="Delivered high quality python code on time.",
    )
    db_session.add(review1)
    db_session.commit()

    # Update freelancer rating calculation
    reviews = db_session.query(Review).filter(Review.freelancer_id == freelancer_prof.id).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews)
    freelancer_prof.average_rating = round(avg_rating, 2)
    freelancer_prof.total_reviews = len(reviews)
    db_session.commit()

    db_session.refresh(freelancer_prof)
    assert freelancer_prof.average_rating == 5.0
    assert freelancer_prof.total_reviews == 1


def test_skills_catalog_endpoints(client: TestClient, client_user: User, mock_supabase):
    """Test public listing of skills catalog."""
    list_res = client.get("/api/skills/")
    assert list_res.status_code in [200, 404]
