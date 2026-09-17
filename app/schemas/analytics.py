from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from uuid import UUID


class PeriodInfo(BaseModel):
    start_date: datetime = Field(..., description="Start date (ISO 8601)")
    end_date: datetime = Field(..., description="End date (ISO 8601)")

class MetricValue(BaseModel):
    value: float = Field(..., description="Metric value")
    unit: str = Field("count", description="Unit of measurement (count, percentage, currency, hours, etc)")
    timestamp: Optional[datetime] = Field(None, description="When this metric was calculated")

class TrendPoint(BaseModel):
    period: datetime = Field(..., description="Period timestamp")
    jobs_created: int = Field(0, ge=0, description="Number of jobs created")
    proposals_submitted: int = Field(0, ge=0, description="Number of proposals submitted")
    contracts_created: int = Field(0, ge=0, description="Number of contracts created")

class JobMetrics(BaseModel):
    """Job activity metrics"""
    created: int = Field(0, ge=0, description="Jobs created in period")
    published: int = Field(0, ge=0, description="Jobs published (actively seeking)")
    completed: int = Field(0, ge=0, description="Jobs completed")
    completion_rate: float = Field(0.0, ge=0, le=100, description="Percentage of published jobs completed")

class ProposalMetrics(BaseModel):
    submitted: int = Field(0, ge=0, description="Total proposals submitted")
    accepted: int = Field(0, ge=0, description="Proposals accepted")
    acceptance_rate: float = Field(0.0, ge=0, le=100, description="Percentage of proposals accepted")


class ContractMetrics(BaseModel):
    created: int = Field(0, ge=0, description="Contracts created")
    completed: int = Field(0, ge=0, description="Contracts completed")
    total_value: float = Field(0.0, ge=0, description="Total contract value ($)")


class UserMetrics(BaseModel):
    active_clients: int = Field(0, ge=0, description="Unique active clients")
    active_freelancers: int = Field(0, ge=0, description="Unique active freelancers")


class MarketplaceAnalyticsResponse(BaseModel):
    period: PeriodInfo = Field(..., description="Time period for metrics")
    jobs: JobMetrics = Field(..., description="Job marketplace activity")
    proposals: ProposalMetrics = Field(..., description="Proposal funnel")
    contracts: ContractMetrics = Field(..., description="Contract activity")
    users: UserMetrics = Field(..., description="User activity")

class JobAnalyticsMetrics(BaseModel):
    created: int = Field(0, ge=0, description="Jobs created")
    published: int = Field(0, ge=0, description="Jobs published")
    completed: int = Field(0, ge=0, description="Jobs completed")
    completion_rate: float = Field(0.0, ge=0, le=100, description="Job completion rate (%)")
    avg_proposals_per_job: float = Field(0.0, ge=0, description="Average proposals per job")
    avg_hours_to_first_proposal: float = Field(0.0, ge=0, description="Average hours until first proposal")


class JobAnalyticsResponse(BaseModel):
    """Job analytics for client"""
    client_id: str = Field(..., description="Client user ID")
    period: PeriodInfo = Field(..., description="Time period")
    jobs: JobAnalyticsMetrics = Field(..., description="Job metrics")

class ProposalFunnel(BaseModel):
    submitted: int = Field(0, ge=0, description="Proposals submitted")
    accepted: int = Field(0, ge=0, description="Proposals accepted")
    rejected: int = Field(0, ge=0, description="Proposals rejected")
    acceptance_rate: float = Field(0.0, ge=0, le=100, description="Acceptance rate (%)")
    rejection_rate: float = Field(0.0, ge=0, le=100, description="Rejection rate (%)")


class ProposalAnalyticsResponse(BaseModel):
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., pattern="^(CLIENT|FREELANCER)$", description="User role")
    period: PeriodInfo = Field(..., description="Time period")
    funnel: ProposalFunnel = Field(..., description="Proposal funnel metrics")

class MilestoneMetrics(BaseModel):
    submitted: int = Field(0, ge=0, description="Milestones submitted")
    approved: int = Field(0, ge=0, description="Milestones approved")
    rejected: int = Field(0, ge=0, description="Milestones rejected")
    approval_rate: float = Field(0.0, ge=0, le=100, description="Approval rate (%)")
    rejection_rate: float = Field(0.0, ge=0, le=100, description="Rejection rate (%)")
    overdue: int = Field(0, ge=0, description="Overdue milestones (not yet approved)")

class MilestoneAnalyticsResponse(BaseModel):
    user_id: str = Field(..., description="User ID")
    role: str = Field(..., pattern="^(CLIENT|FREELANCER)$", description="User role")
    period: PeriodInfo = Field(..., description="Time period")
    milestones: MilestoneMetrics = Field(..., description="Milestone metrics")

class FreelancerPerformance(BaseModel):
    proposals_submitted: int = Field(0, ge=0, description="Total proposals submitted")
    proposals_accepted: int = Field(0, ge=0, description="Proposals accepted")
    success_rate: float = Field(0.0, ge=0, le=100, description="Proposal success rate (%)")
    contracts_completed: int = Field(0, ge=0, description="Contracts completed")
    total_earnings: float = Field(0.0, ge=0, description="Total earnings ($)")
    average_rating: float = Field(0.0, ge=0, le=5, description="Average review rating (1-5)")
    review_count: int = Field(0, ge=0, description="Number of reviews received")
    on_time_delivery_rate: float = Field(0.0, ge=0, le=100, description="On-time delivery rate (%)")

class FreelancerAnalyticsResponse(BaseModel):
    freelancer_id: str = Field(..., description="Freelancer profile ID")
    performance: FreelancerPerformance = Field(..., description="Performance metrics")

class ClientActivity(BaseModel):
    total_jobs_posted: int = Field(0, ge=0, description="Total jobs posted")
    jobs_actively_hiring: int = Field(0, ge=0, description="Jobs currently active (OPEN status)")
    total_proposals_received: int = Field(0, ge=0, description="Total proposals received")
    active_contracts: int = Field(0, ge=0, description="Active/in-progress contracts")
    completed_contracts: int = Field(0, ge=0, description="Completed contracts")
    total_spent: float = Field(0.0, ge=0, description="Total amount spent ($)")
    unique_freelancers_hired: int = Field(0, ge=0, description="Unique freelancers hired")

class ClientAnalyticsResponse(BaseModel):
    client_id: str = Field(..., description="Client user ID")
    activity: ClientActivity = Field(..., description="Activity metrics")

class SkillDemand(BaseModel):
    skill_id: str = Field(..., description="Skill UUID")
    skill_name: str = Field(..., description="Skill name")
    jobs_requesting: int = Field(0, ge=0, description="Number of jobs requesting this skill")
    proposals: int = Field(0, ge=0, description="Number of proposals for jobs with this skill")
    avg_hourly_rate: float = Field(0.0, ge=0, description="Average hourly rate for this skill ($)")
    success_rate: float = Field(0.0, ge=0, le=100, description="Proposal success rate for this skill (%)")


class SkillAnalyticsResponse(BaseModel):
    period: PeriodInfo = Field(..., description="Time period")
    skills: List[SkillDemand] = Field(default_factory=list, description="Top skills by demand")

class TrendAnalyticsResponse(BaseModel):
    granularity: str = Field(..., pattern="^(day|week|month)$", description="Time granularity")
    period: PeriodInfo = Field(..., description="Overall time period")
    trends: List[TrendPoint] = Field(default_factory=list, description="Activity by time period")