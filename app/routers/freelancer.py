from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies.auth import get_current_freelancer_user, get_current_user
from app.models.users import User
from app.models.freelancer_profile import FreelancerProfile
from app.schemas.freelancer import (
    FreelancerProfileCreate, FreelancerProfileUpdate, FreelancerProfileResponse
)
from app.schemas.skill import FreelancerSkillCreate, FreelancerSkillResponse
from app.core.errors import ResourceNotFoundException
import logging
from uuid import UUID
from app.core.errors import ConflictException
from app.models.freelancer_skill import FreelancerSkill
from app.models.skill import Skill
from app.core.errors import ConflictException

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/freelancer", tags=["Freelancer Profile"])


@router.post("/profile", response_model=FreelancerProfileResponse, status_code=201)
async def create_profile_endpoint(profile_data: FreelancerProfileCreate,current_user: User = Depends(get_current_freelancer_user),
                                  db: Session = Depends(get_db)):
    logger.info(f"Creating freelancer profile for user {current_user.id}")
    
    existing = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id,FreelancerProfile.deleted_at == None).first()
    
    if existing:
        raise ConflictException("Freelancer profile already exists")
    
    try:
        profile = FreelancerProfile(user_id=current_user.id,**profile_data.model_dump())
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info(f"Freelancer profile created: {profile.id}")
        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create profile: {str(e)}")
        raise


@router.get("/profile", response_model=FreelancerProfileResponse)
async def get_profile_endpoint(current_user: User = Depends(get_current_freelancer_user),db: Session = Depends(get_db)):
    
    logger.info(f"Fetching profile for user {current_user.id}")
    profile = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id,FreelancerProfile.deleted_at == None).first()
    
    if not profile:
        raise ResourceNotFoundException("Freelancer profile")
    
    return profile


@router.patch("/profile", response_model=FreelancerProfileResponse)
async def update_profile_endpoint(profile_data: FreelancerProfileUpdate,current_user: User = Depends(get_current_freelancer_user),
                                  db: Session = Depends(get_db)):

    logger.info(f"Updating profile for user {current_user.id}")
    profile = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.idFreelancerProfile.deleted_at == None).first()
    
    if not profile:
        raise ResourceNotFoundException("Freelancer profile")
    
    try:
        update_data = profile_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(profile, field, value)
        
        db.commit()
        db.refresh(profile)
        logger.info(f"Profile updated: {profile.id}")
        return profile
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update profile: {str(e)}")
        raise


@router.get("/{freelancer_id}", response_model=FreelancerProfileResponse)
async def get_freelancer_profile_endpoint(freelancer_id: str,db: Session = Depends(get_db)):

    logger.info(f"Fetching freelancer profile: {freelancer_id}")
    profile = db.query(FreelancerProfile).filter(FreelancerProfile.id == freelancer_id,FreelancerProfile.deleted_at == None).first()
    
    if not profile:
        raise ResourceNotFoundException("Freelancer profile")
    
    return profile


@router.post("/profile/skills", response_model=FreelancerSkillResponse, status_code=201)
async def add_skill_endpoint(skill_data: FreelancerSkillCreate,current_user: User = Depends(get_current_freelancer_user),
                             db: Session = Depends(get_db)):
    
    logger.info(f"Adding skill to freelancer {current_user.id}")
    profile = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id,FreelancerProfile.deleted_at == None).first()
    
    if not profile:
        raise ResourceNotFoundException("Freelancer profile")
    
    skill = db.query(Skill).filter(Skill.id == skill_data.skill_id).first()
    
    if not skill:
        raise ResourceNotFoundException("Skill")
    
    existing = db.query(FreelancerSkill).filter(FreelancerSkill.freelancer_id == profile.id,FreelancerSkill.skill_id == skill_data.skill_id).first()
    
    if existing:
        raise ConflictException("Skill already added to profile")
    
    try:
        freelancer_skill = FreelancerSkill(freelancer_id=profile.id,**skill_data.model_dump())
        db.add(freelancer_skill)
        db.commit()
        db.refresh(freelancer_skill)
        logger.info(f"Skill added: {freelancer_skill.id}")
        return freelancer_skill
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to add skill: {str(e)}")
        raise


@router.delete("/profile/skills/{skill_id}", status_code=204)
async def remove_skill_endpoint(skill_id: str,current_user: User = Depends(get_current_freelancer_user),
                                db: Session = Depends(get_db)):
    
    logger.info(f"Removing skill {skill_id} from freelancer {current_user.id}")
    
    profile = db.query(FreelancerProfile).filter(FreelancerProfile.user_id == current_user.id,FreelancerProfile.deleted_at == None).first()
    
    if not profile:
        raise ResourceNotFoundException("Freelancer profile")
    
    freelancer_skill = db.query(FreelancerSkill).filter(FreelancerSkill.freelancer_id == profile.id,FreelancerSkill.skill_id == UUID(skill_id)).first()
    
    if not freelancer_skill:
        raise ResourceNotFoundException("Freelancer skill")
    
    try:
        db.delete(freelancer_skill)
        db.commit()
        logger.info(f"Skill removed: {skill_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to remove skill: {str(e)}")
        raise