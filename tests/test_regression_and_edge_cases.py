import uuid
import pytest
from fastapi.testclient import TestClient
from app.models.users import User
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.contract import Contract, ContractStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.freelancer_profile import FreelancerProfile

def test_cannot_submit_proposal_to_closed_job(client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session):
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Developer')
    db_session.add(freelancer_prof)
    closed_job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Closed Job Title', description='Closed description text', status=JobStatus.CLOSED)
    db_session.add(closed_job)
    db_session.commit()
    mock_supabase['public']._current_mock_user_id = str(freelancer_user.id)
    f_headers = {'Authorization': 'Bearer mock_freelancer_token'}
    res = client.post(f'/proposals/?job_id={closed_job.id}', json={'cover_letter': 'Cover letter for closed job submission', 'proposed_rate': 500.0}, headers=f_headers)
    assert res.status_code == 400

def test_cannot_review_active_or_in_progress_contract(client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session):
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Developer')
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Job Title', description='Description content text')
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter='Letter content text', proposed_rate=1000.0)
    db_session.add(proposal)
    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=proposal.id, client_id=client_user.id, freelancer_id=freelancer_prof.id, title=job.title, total_amount=1000.0, status=ContractStatus.IN_PROGRESS)
    db_session.add(contract)
    db_session.commit()
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    c_headers = {'Authorization': 'Bearer mock_client_token'}
    res = client.post(f'/reviews/?contract_id={contract.id}', json={'rating': 5, 'title': 'Premature Review'}, headers=c_headers)
    assert res.status_code == 400

def test_invalid_rating_boundary_validation(client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session):
    mock_supabase['public']._current_mock_user_id = str(client_user.id)
    c_headers = {'Authorization': 'Bearer mock_client_token'}
    res = client.post(f'/reviews/?contract_id={uuid.uuid4()}', json={'rating': 10, 'title': 'Invalid Rating 10'}, headers=c_headers)
    assert res.status_code in [400, 422]

def test_unassigned_client_cannot_release_milestone_payment(client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session):
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Developer')
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Job Title', description='Description content text')
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter='Letter content text', proposed_rate=1000.0)
    db_session.add(proposal)
    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=proposal.id, client_id=client_user.id, freelancer_id=freelancer_prof.id, title=job.title, total_amount=1000.0, status=ContractStatus.IN_PROGRESS)
    db_session.add(contract)
    milestone = Milestone(id=uuid.uuid4(), contract_id=contract.id, title='Approved Milestone', amount=1000.0, status=MilestoneStatus.APPROVED)
    db_session.add(milestone)
    other_client = User(id=uuid.uuid4(), email='other_client@example.com', username='other_client_user', name='Other Client', role='CLIENT', is_active=True)
    db_session.add(other_client)
    db_session.commit()
    mock_supabase['public']._current_mock_user_id = str(other_client.id)
    other_headers = {'Authorization': 'Bearer mock_other_client_token'}
    res = client.post(f'/milestones/{milestone.id}/release-payment', headers=other_headers)
    assert res.status_code == 403

def test_unassigned_freelancer_cannot_submit_milestone(client: TestClient, client_user: User, freelancer_user: User, mock_supabase, db_session):
    freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=freelancer_user.id, title='Assigned Developer')
    db_session.add(freelancer_prof)
    job = Job(id=uuid.uuid4(), client_id=client_user.id, title='Job Title', description='Description content text')
    db_session.add(job)
    proposal = Proposal(id=uuid.uuid4(), job_id=job.id, freelancer_id=freelancer_prof.id, cover_letter='Letter content text', proposed_rate=1000.0)
    db_session.add(proposal)
    contract = Contract(id=uuid.uuid4(), job_id=job.id, proposal_id=proposal.id, client_id=client_user.id, freelancer_id=freelancer_prof.id, title=job.title, total_amount=1000.0, status=ContractStatus.IN_PROGRESS)
    db_session.add(contract)
    milestone = Milestone(id=uuid.uuid4(), contract_id=contract.id, title='Pending Milestone', amount=1000.0, status=MilestoneStatus.PENDING)
    db_session.add(milestone)
    other_freelancer = User(id=uuid.uuid4(), email='other_freelancer@example.com', username='other_freelancer_user', name='Other Freelancer', role='FREELANCER', is_active=True)
    other_freelancer_prof = FreelancerProfile(id=uuid.uuid4(), user_id=other_freelancer.id, title='Unassigned Dev')
    db_session.add_all([other_freelancer, other_freelancer_prof])
    db_session.commit()
    mock_supabase['public']._current_mock_user_id = str(other_freelancer.id)
    other_f_headers = {'Authorization': 'Bearer mock_other_freelancer_token'}
    res = client.post(f'/milestones/{milestone.id}/submit', headers=other_f_headers)
    assert res.status_code == 403
