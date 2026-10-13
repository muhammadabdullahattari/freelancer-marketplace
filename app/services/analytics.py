from sqlalchemy.orm import Session
from sqlalchemy import func, case, and_, or_, text, extract
from app.models.job import Job, JobStatus
from app.models.proposal import Proposal, ProposalStatus
from app.models.contract import Contract, ContractStatus
from app.models.milestone import Milestone, MilestoneStatus
from app.models.review import Review
from app.models.freelancer_profile import FreelancerProfile
from app.models.users import User
from app.models.job_skill import JobSkill
from app.models.skill import Skill
from app.core.errors import AuthorizationException, BusinessLogicException, ErrorCode
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from decimal import Decimal
import logging
from uuid import UUID

logger = logging.getLogger(__name__)

class AnalyticsService:

    @staticmethod
    def get_marketplace_analytics(db: Session,start_date: datetime,end_date: datetime) -> Dict[str, Any]:
        logger.info(f"Fetching marketplace analytics: {start_date} to {end_date}")

        try:

            jobs_created = db.query(func.count(Job.id)).filter(
                Job.created_at >= start_date,Job.created_at <= end_date,Job.deleted_at == None).scalar() or 0

            jobs_published = db.query(func.count(Job.id)).filter(
                Job.published_at >= start_date,Job.published_at <= end_date,Job.deleted_at == None).scalar() or 0

            jobs_completed = db.query(func.count(Job.id)).filter(Job.closed_at >= start_date,
                Job.closed_at <= end_date,Job.status == JobStatus.COMPLETED,Job.deleted_at == None).scalar() or 0

            completion_rate = (jobs_completed / jobs_published * 100) if jobs_published > 0 else 0.0

            proposals_submitted = db.query(func.count(Proposal.id)).filter(Proposal.created_at >= start_date,
                Proposal.created_at <= end_date,Proposal.deleted_at == None).scalar() or 0

            proposals_accepted = db.query(func.count(Proposal.id)).filter(Proposal.accepted_at >= start_date,
                Proposal.accepted_at <= end_date,Proposal.deleted_at == None).scalar() or 0

            acceptance_rate = (proposals_accepted / proposals_submitted * 100) if proposals_submitted > 0 else 0.0

            total_contract_value = db.query(func.sum(Contract.total_amount)).filter(Contract.created_at >= start_date,
                Contract.created_at <= end_date,Contract.deleted_at == None).scalar() or Decimal('0')

            contracts_completed = db.query(func.count(Contract.id)).filter(Contract.completed_at >= start_date,
                Contract.completed_at <= end_date,Contract.status == ContractStatus.COMPLETED,
                Contract.deleted_at == None).scalar() or 0

            active_clients = db.query(func.count(func.distinct(Job.client_id))).filter(Job.created_at >= start_date,
                Job.created_at <= end_date,Job.deleted_at == None).scalar() or 0

            active_freelancers = db.query(func.count(func.distinct(Proposal.freelancer_id))).filter(
                Proposal.created_at >= start_date,Proposal.created_at <= end_date,
                Proposal.deleted_at == None).scalar() or 0

            return {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "jobs": {
                    "created": jobs_created,
                    "published": jobs_published,
                    "completed": jobs_completed,
                    "completion_rate": round(completion_rate, 2)
                },
                "proposals": {
                    "submitted": proposals_submitted,
                    "accepted": proposals_accepted,
                    "acceptance_rate": round(acceptance_rate, 2)
                },
                "contracts": {
                    "created": db.query(func.count(Contract.id)).filter(
                        Contract.created_at >= start_date,
                        Contract.created_at <= end_date,
                        Contract.deleted_at == None
                    ).scalar() or 0,
                    "completed": contracts_completed,
                    "total_value": float(total_contract_value)
                },
                "users": {
                    "active_clients": active_clients,
                    "active_freelancers": active_freelancers
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch marketplace analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Analytics failed: {str(e)}")

    @staticmethod
    def get_job_analytics(db: Session, client_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        logger.info(f"Fetching job analytics for client {client_id}")

        try:
            
            client_uuid = UUID(client_id)

            client = db.query(User).filter(User.id == client_uuid).first()
            if not client or client.role != "CLIENT":
                raise AuthorizationException("Only clients can view job analytics")

            jobs_created = db.query(func.count(Job.id)).filter(
                Job.client_id == client_uuid,
                Job.created_at >= start_date,
                Job.created_at <= end_date,
                Job.deleted_at == None
            ).scalar() or 0

            jobs_published = db.query(func.count(Job.id)).filter(
                Job.client_id == client_uuid,
                Job.published_at >= start_date,
                Job.published_at <= end_date,
                Job.deleted_at == None
            ).scalar() or 0

            jobs_completed = db.query(func.count(Job.id)).filter(
                Job.client_id == client_uuid,
                Job.closed_at >= start_date,
                Job.closed_at <= end_date,
                Job.status == JobStatus.COMPLETED,
                Job.deleted_at == None
            ).scalar() or 0

            completion_rate = (jobs_completed / jobs_published * 100) if jobs_published > 0 else 0.0

            avg_proposals = db.query(
                func.avg(
                    db.query(func.count(Proposal.id)).filter(
                        Proposal.job_id == Job.id,
                        Proposal.deleted_at == None
                    ).correlate(Job).scalar_subquery()
                )
            ).filter(
                Job.client_id == client_uuid,
                Job.created_at >= start_date,
                Job.created_at <= end_date,
                Job.deleted_at == None
            ).scalar() or 0.0

            avg_time_to_proposal = db.query(
                func.avg(
                    extract('epoch',
                        db.query(func.min(Proposal.created_at))
                            .filter(Proposal.job_id == Job.id, Proposal.deleted_at == None)
                            .correlate(Job)
                            .scalar_subquery() - Job.published_at
                    ) / 3600
                )
            ).filter(
                Job.client_id == client_uuid,
                Job.published_at >= start_date,
                Job.published_at <= end_date,
                Job.published_at != None,
                Job.deleted_at == None
            ).scalar() or 0.0

            return {
                "client_id": client_id,
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "jobs": {
                    "created": jobs_created,
                    "published": jobs_published,
                    "completed": jobs_completed,
                    "completion_rate": round(completion_rate, 2),
                    "avg_proposals_per_job": round(float(avg_proposals), 2),
                    "avg_hours_to_first_proposal": round(float(avg_time_to_proposal), 1)
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch job analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Job analytics failed: {str(e)}")

    @staticmethod
    def get_proposal_analytics(db: Session,user_id: str,role: str,start_date: datetime,end_date: datetime) -> Dict[str, Any]:
        logger.info(f"Fetching proposal analytics for {role} {user_id}")

        try:
            
            user_uuid = UUID(user_id)

            if role == "CLIENT":

                proposals_submitted = db.query(func.count(Proposal.id)).filter(
                    Proposal.job_id.in_(
                        db.query(Job.id).filter(Job.client_id == user_uuid, Job.deleted_at == None)
                    ),
                    Proposal.created_at >= start_date,
                    Proposal.created_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0

                proposals_accepted = db.query(func.count(Proposal.id)).filter(
                    Proposal.job_id.in_(
                        db.query(Job.id).filter(Job.client_id == user_uuid, Job.deleted_at == None)
                    ),
                    Proposal.status == ProposalStatus.ACCEPTED,
                    Proposal.accepted_at >= start_date,
                    Proposal.accepted_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0

                proposals_rejected = db.query(func.count(Proposal.id)).filter(
                    Proposal.job_id.in_(
                        db.query(Job.id).filter(Job.client_id == user_uuid, Job.deleted_at == None)
                    ),
                    Proposal.status == ProposalStatus.REJECTED,
                    Proposal.rejected_at >= start_date,
                    Proposal.rejected_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0

            elif role == "FREELANCER":

                freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == user_uuid).first()
                if not freelancer:
                    raise AuthorizationException("Freelancer profile not found")

                proposals_submitted = db.query(func.count(Proposal.id)).filter(
                    Proposal.freelancer_id == freelancer.id,
                    Proposal.created_at >= start_date,
                    Proposal.created_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0

                proposals_accepted = db.query(func.count(Proposal.id)).filter(
                    Proposal.freelancer_id == freelancer.id,
                    Proposal.status == ProposalStatus.ACCEPTED,
                    Proposal.accepted_at >= start_date,
                    Proposal.accepted_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0

                proposals_rejected = db.query(func.count(Proposal.id)).filter(
                    Proposal.freelancer_id == freelancer.id,
                    Proposal.status == ProposalStatus.REJECTED,
                    Proposal.rejected_at >= start_date,
                    Proposal.rejected_at <= end_date,
                    Proposal.deleted_at == None
                ).scalar() or 0
            else:
                raise AuthorizationException("Invalid role")

            acceptance_rate = (proposals_accepted / proposals_submitted * 100) if proposals_submitted > 0 else 0.0
            rejection_rate = (proposals_rejected / proposals_submitted * 100) if proposals_submitted > 0 else 0.0

            return {
                "user_id": user_id,
                "role": role,
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "funnel": {
                    "submitted": proposals_submitted,
                    "accepted": proposals_accepted,
                    "rejected": proposals_rejected,
                    "acceptance_rate": round(acceptance_rate, 2),
                    "rejection_rate": round(rejection_rate, 2)
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch proposal analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Proposal analytics failed: {str(e)}")

    @staticmethod
    def get_milestone_analytics(db: Session,user_id: str,role: str,start_date: datetime,end_date: datetime) -> Dict[str, Any]:
        logger.info(f"Fetching milestone analytics for {role} {user_id}")

        try:
            
            user_uuid = UUID(user_id)

            if role == "CLIENT":
                milestones_submitted = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.client_id == user_uuid,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.submitted_at >= start_date,
                    Milestone.submitted_at <= end_date
                ).scalar() or 0

                milestones_approved = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.client_id == user_uuid,
                            Contract.deleted_at == None
                        )
                    ),
                    or_(
                        Milestone.status.in_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED]),
                        and_(Milestone.approved_at >= start_date, Milestone.approved_at <= end_date)
                    )
                ).scalar() or 0

                milestones_rejected = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.client_id == user_uuid,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.status == MilestoneStatus.REJECTED
                ).scalar() or 0

                overdue_milestones = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.client_id == user_uuid,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.due_date < datetime.now(timezone.utc),
                    Milestone.status.notin_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED]),
                    Milestone.approved_at == None
                ).scalar() or 0

            elif role == "FREELANCER":
                freelancer = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == user_uuid).first()
                if not freelancer:
                    raise AuthorizationException("Freelancer profile not found")

                milestones_submitted = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.freelancer_id == freelancer.id,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.submitted_at >= start_date,
                    Milestone.submitted_at <= end_date
                ).scalar() or 0

                milestones_approved = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.freelancer_id == freelancer.id,
                            Contract.deleted_at == None
                        )
                    ),
                    or_(
                        Milestone.status.in_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED]),
                        and_(Milestone.approved_at >= start_date, Milestone.approved_at <= end_date)
                    )
                ).scalar() or 0

                milestones_rejected = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.freelancer_id == freelancer.id,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.status == MilestoneStatus.REJECTED
                ).scalar() or 0

                overdue_milestones = db.query(func.count(Milestone.id)).filter(
                    Milestone.contract_id.in_(
                        db.query(Contract.id).filter(
                            Contract.freelancer_id == freelancer.id,
                            Contract.deleted_at == None
                        )
                    ),
                    Milestone.due_date < datetime.now(timezone.utc),
                    Milestone.status.notin_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED]),
                    Milestone.approved_at == None
                ).scalar() or 0

            approval_rate = (milestones_approved / milestones_submitted * 100) if milestones_submitted > 0 else 0.0
            rejection_rate = (milestones_rejected / milestones_submitted * 100) if milestones_submitted > 0 else 0.0

            return {
                "user_id": user_id,
                "role": role,
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "milestones": {
                    "submitted": milestones_submitted,
                    "approved": milestones_approved,
                    "rejected": milestones_rejected,
                    "approval_rate": round(approval_rate, 2),
                    "rejection_rate": round(rejection_rate, 2),
                    "overdue": overdue_milestones
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch milestone analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Milestone analytics failed: {str(e)}")

    @staticmethod
    def get_freelancer_analytics(db: Session,freelancer_id: str) -> Dict[str, Any]:
        logger.info(f"Fetching freelancer analytics for {freelancer_id}")

        try:
            
            freelancer_uuid = UUID(freelancer_id)

            freelancer = db.query(FreelancerProfile).filter(
                FreelancerProfile.id == freelancer_uuid
            ).first()

            if not freelancer:
                raise BusinessLogicException(ErrorCode.NOT_FOUND, "Freelancer not found")

            proposals_submitted = db.query(func.count(Proposal.id)).filter(
                Proposal.freelancer_id == freelancer_uuid,
                Proposal.deleted_at == None
            ).scalar() or 0

            proposals_accepted = db.query(func.count(Proposal.id)).filter(
                Proposal.freelancer_id == freelancer_uuid,
                Proposal.status == ProposalStatus.ACCEPTED,
                Proposal.deleted_at == None
            ).scalar() or 0

            success_rate = (proposals_accepted / proposals_submitted * 100) if proposals_submitted > 0 else 0.0

            contracts_completed = db.query(func.count(Contract.id)).filter(
                Contract.freelancer_id == freelancer_uuid,
                Contract.status == ContractStatus.COMPLETED,
                Contract.deleted_at == None
            ).scalar() or 0

            total_earnings = db.query(func.sum(Contract.total_amount)).filter(
                Contract.freelancer_id == freelancer_uuid,
                Contract.status == ContractStatus.COMPLETED,
                Contract.deleted_at == None
            ).scalar() or Decimal('0')

            avg_rating = db.query(func.avg(Review.rating)).filter(
                Review.freelancer_id == freelancer_uuid
            ).scalar() or 0.0

            review_count = db.query(func.count(Review.id)).filter(
                Review.freelancer_id == freelancer_uuid
            ).scalar() or 0

            on_time_milestones = db.query(func.count(Milestone.id)).filter(
                Milestone.contract_id.in_(
                    db.query(Contract.id).filter(
                        Contract.freelancer_id == freelancer_uuid,
                        Contract.deleted_at == None
                    )
                ),
                Milestone.status.in_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED]),
                Milestone.approved_at <= Milestone.due_date
            ).scalar() or 0

            total_milestones = db.query(func.count(Milestone.id)).filter(
                Milestone.contract_id.in_(
                    db.query(Contract.id).filter(
                        Contract.freelancer_id == freelancer_uuid,
                        Contract.deleted_at == None
                    )
                ),
                Milestone.status.in_([MilestoneStatus.APPROVED, MilestoneStatus.PAYMENT_RELEASED])
            ).scalar() or 0

            on_time_rate = (on_time_milestones / total_milestones * 100) if total_milestones > 0 else 0.0

            return {
                "freelancer_id": freelancer_id,
                "performance": {
                    "proposals_submitted": proposals_submitted,
                    "proposals_accepted": proposals_accepted,
                    "success_rate": round(success_rate, 2),
                    "contracts_completed": contracts_completed,
                    "total_earnings": float(total_earnings),
                    "average_rating": round(float(avg_rating), 2),
                    "review_count": review_count,
                    "on_time_delivery_rate": round(on_time_rate, 2)
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch freelancer analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Freelancer analytics failed: {str(e)}")

    @staticmethod
    def get_client_analytics(db: Session,client_id: str) -> Dict[str, Any]:
        logger.info(f"Fetching client analytics for {client_id}")

        try:
            
            client_uuid = UUID(client_id)

            client = db.query(User).filter(User.id == client_uuid).first()
            if not client or client.role != "CLIENT":
                raise AuthorizationException("Only clients can view client analytics")

            total_jobs = db.query(func.count(Job.id)).filter(
                Job.client_id == client_uuid,
                Job.deleted_at == None
            ).scalar() or 0

            jobs_published = db.query(func.count(Job.id)).filter(
                Job.client_id == client_uuid,
                Job.status == JobStatus.OPEN,
                Job.deleted_at == None
            ).scalar() or 0

            total_proposals = db.query(func.count(Proposal.id)).filter(
                Proposal.job_id.in_(
                    db.query(Job.id).filter(Job.client_id == client_uuid, Job.deleted_at == None)
                ),
                Proposal.deleted_at == None
            ).scalar() or 0

            active_contracts = db.query(func.count(Contract.id)).filter(
                Contract.client_id == client_uuid,
                Contract.status.in_([ContractStatus.ACTIVE, ContractStatus.IN_PROGRESS]),
                Contract.deleted_at == None
            ).scalar() or 0

            completed_contracts = db.query(func.count(Contract.id)).filter(
                Contract.client_id == client_uuid,
                Contract.status == ContractStatus.COMPLETED,
                Contract.deleted_at == None
            ).scalar() or 0

            total_spent = db.query(func.sum(Contract.total_amount)).filter(
                Contract.client_id == client_uuid,
                Contract.deleted_at == None
            ).scalar() or Decimal('0')

            freelancers_hired = db.query(func.count(func.distinct(Contract.freelancer_id))).filter(
                Contract.client_id == client_uuid,
                Contract.deleted_at == None
            ).scalar() or 0

            return {
                "client_id": client_id,
                "activity": {
                    "total_jobs_posted": total_jobs,
                    "jobs_actively_hiring": jobs_published,
                    "total_proposals_received": total_proposals,
                    "active_contracts": active_contracts,
                    "completed_contracts": completed_contracts,
                    "total_spent": float(total_spent),
                    "unique_freelancers_hired": freelancers_hired
                }
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch client analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Client analytics failed: {str(e)}")

    @staticmethod
    def get_skill_analytics(db: Session,start_date: datetime,end_date: datetime,limit: int = 50) -> Dict[str, Any]:
        logger.info(f"Fetching skill analytics")

        try:

            top_skills = db.query(
                Skill.id,
                Skill.name,
                func.count(func.distinct(Job.id)).label('job_count'),
                func.count(func.distinct(Proposal.id)).label('proposal_count'),
                func.avg(Proposal.proposed_rate).label('avg_rate'),
                func.count(func.distinct(case((Proposal.status == ProposalStatus.ACCEPTED, Proposal.id), else_=None))).label('accepted_count')
            ).join(JobSkill, JobSkill.skill_id == Skill.id).join(
                Job, Job.id == JobSkill.job_id
            ).outerjoin(
                Proposal, Proposal.job_id == Job.id
            ).filter(
                Job.created_at >= start_date,
                Job.created_at <= end_date,
                Job.deleted_at == None
            ).group_by(Skill.id, Skill.name).order_by(
                func.count(func.distinct(Job.id)).desc()
            ).limit(limit).all()

            skills_data = [
                {
                    "skill_id": str(skill[0]),
                    "skill_name": skill[1],
                    "jobs_requesting": skill[2],
                    "proposals": skill[3],
                    "avg_hourly_rate": float(skill[4]) if skill[4] else 0.0,
                    "success_rate": round(min(100.0, (skill[5] / skill[3] * 100.0)), 2) if (skill[3] and skill[3] > 0) else 0.0
                }
                for skill in top_skills
            ]

            return {
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "skills": skills_data
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch skill analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Skill analytics failed: {str(e)}")

    @staticmethod
    def get_trend_analytics(db: Session,start_date: datetime,end_date: datetime,granularity: str = "day") -> Dict[str, Any]:
        logger.info(f"Fetching trend analytics (granularity: {granularity})")

        try:
            jobs_by_date = db.query(
                func.date(Job.created_at).label('period'),
                func.count(Job.id).label('jobs_created')
            ).filter(
                Job.created_at >= start_date,
                Job.created_at <= end_date,
                Job.deleted_at == None
            ).group_by(func.date(Job.created_at)).all()

            proposals_by_date = db.query(
                func.date(Proposal.created_at).label('period'),
                func.count(Proposal.id).label('proposals_submitted')
            ).filter(
                Proposal.created_at >= start_date,
                Proposal.created_at <= end_date,
                Proposal.deleted_at == None
            ).group_by(func.date(Proposal.created_at)).all()

            contracts_by_date = db.query(
                func.date(Contract.created_at).label('period'),
                func.count(Contract.id).label('contracts_created')
            ).filter(
                Contract.created_at >= start_date,
                Contract.created_at <= end_date,
                Contract.deleted_at == None
            ).group_by(func.date(Contract.created_at)).all()

            trends_map: Dict[str, Dict[str, int]] = {}

            for row in jobs_by_date:
                if row[0]:
                    d_str = str(row[0])
                    trends_map.setdefault(d_str, {"jobs_created": 0, "proposals_submitted": 0, "contracts_created": 0})["jobs_created"] = row[1]

            for row in proposals_by_date:
                if row[0]:
                    d_str = str(row[0])
                    trends_map.setdefault(d_str, {"jobs_created": 0, "proposals_submitted": 0, "contracts_created": 0})["proposals_submitted"] = row[1]

            for row in contracts_by_date:
                if row[0]:
                    d_str = str(row[0])
                    trends_map.setdefault(d_str, {"jobs_created": 0, "proposals_submitted": 0, "contracts_created": 0})["contracts_created"] = row[1]

            trend_data = [
                {
                    "period": f"{d_key}T00:00:00Z" if len(d_key) == 10 else d_key,
                    "jobs_created": metrics["jobs_created"],
                    "proposals_submitted": metrics["proposals_submitted"],
                    "contracts_created": metrics["contracts_created"]
                }
                for d_key, metrics in sorted(trends_map.items())
            ]

            return {
                "granularity": granularity,
                "period": {"start_date": start_date.isoformat(), "end_date": end_date.isoformat()},
                "trends": trend_data
            }

        except (AuthorizationException, BusinessLogicException):
            raise
        except Exception as e:
            logger.error(f"Failed to fetch trend analytics: {str(e)}", exc_info=True)
            raise BusinessLogicException(ErrorCode.INTERNAL_ERROR, f"Trend analytics failed: {str(e)}")
