import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User
from app.models.contract import Contract, ContractStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.freelancer_profile import FreelancerProfile
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus


def test_contract_milestone_payment_and_amount_paid_data_consistency(
    client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session
):
    """Test full contract integration flow and data consistency for amount_paid."""
    # 1. Create Freelancer Profile
    freelancer_prof = FreelancerProfile(
        id=uuid.uuid4(),
        user_id=freelancer_user.id,
        bio="Test freelancer bio statement",
        title="Full Stack Engineer",
        hourly_rate=60.0,
    )
    db_session.add(freelancer_prof)

    # 2. Create Job & Proposal
    job = Job(
        id=uuid.uuid4(),
        client_id=client_user.id,
        title="Full Lifecycle E-Commerce Project",
        description="Detailed project requirements for contract lifecycle testing.",
        status=JobStatus.OPEN,
    )
    db_session.add(job)

    proposal = Proposal(
        id=uuid.uuid4(),
        job_id=job.id,
        freelancer_id=freelancer_prof.id,
        cover_letter="Cover letter for full contract lifecycle test.",
        proposed_rate=2000.0,
        status=ProposalStatus.ACCEPTED,
    )
    db_session.add(proposal)

    # 3. Create Contract
    contract = Contract(
        id=uuid.uuid4(),
        job_id=job.id,
        proposal_id=proposal.id,
        client_id=client_user.id,
        freelancer_id=freelancer_prof.id,
        title=job.title,
        description=job.description,
        total_amount=2000.0,
        amount_paid=0.0,
        status=ContractStatus.IN_PROGRESS,
    )
    db_session.add(contract)

    # 4. Create Milestone 1 ($1000)
    milestone1 = Milestone(
        id=uuid.uuid4(),
        contract_id=contract.id,
        title="Milestone 1: Backend Architecture Setup",
        amount=1000.0,
        status=MilestoneStatus.APPROVED,
        order=1,
    )
    db_session.add(milestone1)
    db_session.commit()

    # Assert initial amount_paid is 0
    assert contract.amount_paid == 0.0

    # 5. Release Payment for Milestone 1 via Endpoint
    mock_supabase["public"]._current_mock_user_id = str(client_user.id)
    c_headers = {"Authorization": "Bearer mock_client_token"}
    pay_res = client.post(f"/api/milestones/{milestone1.id}/release-payment", headers=c_headers)
    assert pay_res.status_code == 200
    assert pay_res.json()["status"] == "PAYMENT_RELEASED"

    # 6. Verify DATA CONSISTENCY: contract.amount_paid must equal 1000.0!
    db_session.refresh(contract)
    assert contract.amount_paid == 1000.0


def test_cannot_complete_contract_with_pending_milestones(
    client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session
):
    """Test completing a contract fails (400 Bad Request) if milestones are still PENDING."""
    freelancer_prof = FreelancerProfile(
        id=uuid.uuid4(),
        user_id=freelancer_user.id,
        title="Developer",
    )
    db_session.add(freelancer_prof)

    job = Job(id=uuid.uuid4(), client_id=client_user.id, title="Job Title", description="Description text long enough")
    db_session.add(job)

    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter="Letter content text", proposed_rate=500.0)
    db_session.add(proposal)

    contract = Contract(
        id=uuid.uuid4(),
        job_id=job.id,
        proposal_id=proposal.id,
        client_id=client_user.id,
        freelancer_id=freelancer_prof.id,
        title="Test Contract",
        total_amount=500.0,
        status=ContractStatus.IN_PROGRESS,
    )
    db_session.add(contract)

    # Add unapproved/pending milestone
    pending_m = Milestone(
        id=uuid.uuid4(),
        contract_id=contract.id,
        title="Unapproved Milestone",
        amount=500.0,
        status=MilestoneStatus.PENDING,
    )
    db_session.add(pending_m)
    db_session.commit()

    mock_supabase["public"]._current_mock_user_id = str(client_user.id)
    c_headers = {"Authorization": "Bearer mock_client_token"}
    comp_res = client.post(f"/api/contracts/{contract.id}/complete", headers=c_headers)
    assert comp_res.status_code == 400
    error_text = comp_res.json().get("message") or comp_res.json().get("detail") or ""
    assert "milestones" in str(error_text).lower() or "pending" in str(error_text).lower()
