from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.skill import Skill
from app.schemas.skill import SkillCreate, SkillUpdate, SkillResponse
from app.core.errors import ResourceNotFoundException, ConflictException, BusinessLogicException, ErrorCode
import logging
from uuid import UUID
from app.models.freelancer_skill import FreelancerSkill
from app.models.job_skill import JobSkill
    
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/skills", tags=["Skills"])

@router.post("/", response_model=SkillResponse, status_code=201)
def create_skill_endpoint(skill_data: SkillCreate,db: Session = Depends(get_db)):
    
    logger.info(f"Creating skill: {skill_data.name}")
    existing = db.query(Skill).filter(Skill.name.ilike(skill_data.name)).first()
    
    if existing:
        raise ConflictException("Skill with this name already exists")
    
    try:
        skill = Skill(**skill_data.model_dump())
        db.add(skill)
        db.commit()
        db.refresh(skill)
        logger.info(f"Skill created: {skill.id}")
        return skill
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to create skill: {str(e)}")
        raise

@router.get("/{skill_id}", response_model=SkillResponse)
def get_skill_endpoint(skill_id: str,db: Session = Depends(get_db)):

    logger.info(f"Fetching skill: {skill_id}")    
    skill = db.query(Skill).filter(Skill.id == UUID(skill_id)).first()
    
    if not skill:
        raise ResourceNotFoundException("Skill")
    
    return skill

@router.patch("/{skill_id}", response_model=SkillResponse)
def update_skill_endpoint(skill_id: str,skill_data: SkillUpdate,db: Session = Depends(get_db)):
    
    logger.info(f"Updating skill: {skill_id}")
    skill = db.query(Skill).filter(Skill.id == UUID(skill_id)).first()
    
    if not skill:
        raise ResourceNotFoundException("Skill")
    
    try:
        update_data = skill_data.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            setattr(skill, field, value)
        
        db.commit()
        db.refresh(skill)
        logger.info(f"Skill updated: {skill_id}")
        return skill
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to update skill: {str(e)}")
        raise

@router.delete("/{skill_id}", status_code=204)
def delete_skill_endpoint(skill_id: str,db: Session = Depends(get_db)):
    
    logger.info(f"Deleting skill: {skill_id}")    
    skill = db.query(Skill).filter(Skill.id == UUID(skill_id)).first()
    
    if not skill:
        raise ResourceNotFoundException("Skill")
    
    in_use = db.query(FreelancerSkill).filter(FreelancerSkill.skill_id == UUID(skill_id)).first()
    
    if in_use:
        raise BusinessLogicException(ErrorCode.INVALID_OPERATION,"Cannot delete skill that is in use by freelancers")
    
    in_use_jobs = db.query(JobSkill).filter(JobSkill.skill_id == UUID(skill_id)).first()
    
    if in_use_jobs:
        raise BusinessLogicException(ErrorCode.INVALID_OPERATION,"Cannot delete skill that is required by jobs")
    
    try:
        db.delete(skill)
        db.commit()
        logger.info(f"Skill deleted: {skill_id}")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete skill: {str(e)}")
        raise

@router.get("/", response_model=list[SkillResponse])
def list_skills_endpoint(skip: int = Query(0, ge=0),limit: int = Query(100, ge=1, le=1000),
                               search: str = Query(None),db: Session = Depends(get_db)):
    
    logger.info(f"Listing skills - skip: {skip}, limit: {limit}")
    query = db.query(Skill)
    
    if search:
        query = query.filter(Skill.name.ilike(f"%{search}%"))
    
    skills = query.order_by(Skill.name).offset(skip).limit(limit).all()
    
    return skills