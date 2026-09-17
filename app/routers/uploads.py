import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.errors import AuthorizationException, BusinessLogicException, ErrorCode, ResourceNotFoundException
from app.core.file_config import FileType
from app.database import get_db
from app.dependencies.auth import get_current_client_user, get_current_freelancer_user, get_current_user
from app.models.contract import Contract
from app.models.file_upload import FileUpload
from app.models.freelancer_profile import FreelancerProfile
from app.models.milestone import Milestone
from app.models.proposal import Proposal
from app.models.users import User
from app.schemas.file import (
    ContractDocumentResponse,
    FileUploadResponse,
    MilestoneDeliverableResponse,
    ProfilePictureUploadResponse,
    ProposalAttachmentResponse,
)
from app.services.file_storage import FileStorageService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/uploads", tags=["File Uploads"])


@router.post("/profile-picture", response_model=ProfilePictureUploadResponse, status_code=201)
async def upload_profile_picture(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Uploading profile picture for user: {current_user.id}")
    
    existing_picture = db.query(FileUpload).filter(
        FileUpload.user_id == current_user.id,
        FileUpload.file_type == FileType.PROFILE_PICTURE.value,
        FileUpload.deleted_at == None
    ).first()
    
    if existing_picture:
        raise BusinessLogicException(
            ErrorCode.ALREADY_EXISTS,
            "Profile picture already exists"
        )
    
    file_upload = await FileStorageService.upload_file(
        file=file,
        file_type=FileType.PROFILE_PICTURE,
        uploaded_by_user_id=current_user.id,
        db=db,
        user_id=current_user.id
    )
    
    return {
        "id": file_upload.id,
        "url": file_upload.storage_url,
        "filename": file_upload.original_filename,
        "file_size_bytes": file_upload.file_size_bytes,
        "created_at": file_upload.created_at
    }


@router.get("/profile-picture/{user_id}", response_model=ProfilePictureUploadResponse)
def get_profile_picture(user_id: UUID, db: Session = Depends(get_db)):
    logger.info(f"Fetching profile picture for user: {user_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.user_id == user_id,
        FileUpload.file_type == FileType.PROFILE_PICTURE.value,
        FileUpload.deleted_at == None
    ).order_by(FileUpload.created_at.desc()).first()
    
    if not file_upload:
        raise ResourceNotFoundException("Profile picture")
    
    return {
        "id": file_upload.id,
        "url": file_upload.storage_url,
        "filename": file_upload.original_filename,
        "file_size_bytes": file_upload.file_size_bytes,
        "created_at": file_upload.created_at
    }


@router.delete("/profile-picture/{file_id}", status_code=204)
def delete_profile_picture(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Deleting profile picture: {file_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.id == file_id,
        FileUpload.uploaded_by_user_id == current_user.id,
        FileUpload.deleted_at == None
    ).first()
    
    if not file_upload:
        raise ResourceNotFoundException("Profile picture")
    
    FileStorageService.delete_file(file_upload, db)


@router.post("/proposal/{proposal_id}/attachment", response_model=ProposalAttachmentResponse, status_code=201)
async def upload_proposal_attachment(
    proposal_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Uploading attachment to proposal: {proposal_id}")    
    
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.deleted_at == None
    ).first()
    
    if not proposal:
        raise ResourceNotFoundException("Proposal")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    if not freelancer or proposal.freelancer_id != freelancer.id:
        raise AuthorizationException("You can only upload attachments to your own proposals")
    
    file_upload = await FileStorageService.upload_file(
        file=file,
        file_type=FileType.PROPOSAL_ATTACHMENT,
        uploaded_by_user_id=current_user.id,
        db=db,
        proposal_id=proposal_id
    )
    
    return {
        "id": file_upload.id,
        "filename": file_upload.filename,
        "original_filename": file_upload.original_filename,
        "file_size_bytes": file_upload.file_size_bytes,
        "mime_type": file_upload.mime_type,
        "created_at": file_upload.created_at
    }


@router.get("/proposal/{proposal_id}/attachments", response_model=list[ProposalAttachmentResponse])
def get_proposal_attachments(
    proposal_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching attachments for proposal: {proposal_id}")
    
    proposal = db.query(Proposal).filter(
        Proposal.id == proposal_id,
        Proposal.deleted_at == None
    ).first()
    
    if not proposal:
        raise ResourceNotFoundException("Proposal")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = proposal.job.client_id == current_user.id
    is_freelancer = freelancer and proposal.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to view attachments for this proposal")

    attachments = db.query(FileUpload).filter(
        FileUpload.proposal_id == proposal_id,
        FileUpload.file_type == FileType.PROPOSAL_ATTACHMENT.value,
        FileUpload.deleted_at == None
    ).order_by(FileUpload.created_at.desc()).all()
    
    return [
        {
            "id": a.id,
            "filename": a.filename,
            "original_filename": a.original_filename,
            "file_size_bytes": a.file_size_bytes,
            "mime_type": a.mime_type,
            "created_at": a.created_at
        }
        for a in attachments
    ]


@router.delete("/proposal/attachment/{file_id}", status_code=204)
def delete_proposal_attachment(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Deleting attachment: {file_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.id == file_id,
        FileUpload.uploaded_by_user_id == current_user.id,
        FileUpload.deleted_at == None
    ).first()
    
    if not file_upload:
        raise ResourceNotFoundException("Attachment")
    
    FileStorageService.delete_file(file_upload, db)


@router.post("/contract/{contract_id}/document", response_model=ContractDocumentResponse, status_code=201)
async def upload_contract_document(
    contract_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Uploading document to contract: {contract_id}")
    
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.deleted_at == None
    ).first()
    
    if not contract:
        raise ResourceNotFoundException("Contract")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = contract.client_id == current_user.id
    is_freelancer = freelancer and contract.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to upload documents for this contract")
    
    file_upload = await FileStorageService.upload_file(
        file=file,
        file_type=FileType.CONTRACT_DOCUMENT,
        uploaded_by_user_id=current_user.id,
        db=db,
        contract_id=contract_id
    )
    
    return {
        "id": file_upload.id,
        "filename": file_upload.filename,
        "original_filename": file_upload.original_filename,
        "file_size_bytes": file_upload.file_size_bytes,
        "mime_type": file_upload.mime_type,
        "created_at": file_upload.created_at
    }


@router.get("/contract/{contract_id}/documents", response_model=list[ContractDocumentResponse])
def get_contract_documents(
    contract_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching documents for contract: {contract_id}")
    
    contract = db.query(Contract).filter(
        Contract.id == contract_id,
        Contract.deleted_at == None
    ).first()
    
    if not contract:
        raise ResourceNotFoundException("Contract")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = contract.client_id == current_user.id
    is_freelancer = freelancer and contract.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to view documents for this contract")
    
    documents = db.query(FileUpload).filter(
        FileUpload.contract_id == contract_id,
        FileUpload.file_type == FileType.CONTRACT_DOCUMENT.value,
        FileUpload.deleted_at == None
    ).order_by(FileUpload.created_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "original_filename": d.original_filename,
            "file_size_bytes": d.file_size_bytes,
            "mime_type": d.mime_type,
            "created_at": d.created_at
        }
        for d in documents
    ]


@router.delete("/contract/document/{file_id}", status_code=204)
def delete_contract_document(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete contract document"""
    logger.info(f"Deleting contract document: {file_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.id == file_id,
        FileUpload.deleted_at == None
    ).first()
    
    if not file_upload:
        raise ResourceNotFoundException("Document")
    
    if not file_upload.contract_id:
        raise BusinessLogicException(
            ErrorCode.INVALID_OPERATION,
            "This is not a contract document"
        )
    
    contract = db.query(Contract).filter(
        Contract.id == file_upload.contract_id
    ).first()
    
    if not contract:
        raise ResourceNotFoundException("Contract")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = contract.client_id == current_user.id
    is_freelancer = freelancer and contract.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to delete documents from this contract")
    
    FileStorageService.delete_file(file_upload, db)


@router.post("/milestone/{milestone_id}/deliverable", response_model=MilestoneDeliverableResponse, status_code=201)
async def upload_milestone_deliverable(
    milestone_id: UUID,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Uploading deliverable to milestone: {milestone_id}")
    
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id
    ).first()
    
    if not milestone:
        raise ResourceNotFoundException("Milestone")
    
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id,
        FreelancerProfile.id == milestone.contract.freelancer_id
    ).first()
    
    if not freelancer:
        raise AuthorizationException("Only the freelancer can upload deliverables for this milestone")
    
    file_upload = await FileStorageService.upload_file(
        file=file,
        file_type=FileType.MILESTONE_DELIVERABLE,
        uploaded_by_user_id=current_user.id,
        db=db,
        milestone_id=milestone_id
    )
    
    return {
        "id": file_upload.id,
        "filename": file_upload.filename,
        "original_filename": file_upload.original_filename,
        "file_size_bytes": file_upload.file_size_bytes,
        "mime_type": file_upload.mime_type,
        "created_at": file_upload.created_at
    }


@router.get("/milestone/{milestone_id}/deliverables", response_model=list[MilestoneDeliverableResponse])
def get_milestone_deliverables(
    milestone_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logger.info(f"Fetching deliverables for milestone: {milestone_id}")
    
    milestone = db.query(Milestone).filter(
        Milestone.id == milestone_id
    ).first()
    
    if not milestone:
        raise ResourceNotFoundException("Milestone")
    
    contract = milestone.contract
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = contract.client_id == current_user.id
    is_freelancer = freelancer and contract.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to view deliverables for this milestone")
    
    deliverables = db.query(FileUpload).filter(
        FileUpload.milestone_id == milestone_id,
        FileUpload.file_type == FileType.MILESTONE_DELIVERABLE.value,
        FileUpload.deleted_at == None
    ).order_by(FileUpload.created_at.desc()).all()
    
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "original_filename": d.original_filename,
            "file_size_bytes": d.file_size_bytes,
            "mime_type": d.mime_type,
            "created_at": d.created_at
        }
        for d in deliverables
    ]


@router.delete("/milestone/deliverable/{file_id}", status_code=204)
def delete_milestone_deliverable(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete milestone deliverable"""
    logger.info(f"Deleting milestone deliverable: {file_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.id == file_id,
        FileUpload.deleted_at == None
    ).first()
    
    if not file_upload:
        raise ResourceNotFoundException("Deliverable")
    
    if not file_upload.milestone_id:
        raise BusinessLogicException(
            ErrorCode.INVALID_OPERATION,
            "This is not a milestone deliverable"
        )
    
    milestone = db.query(Milestone).filter(
        Milestone.id == file_upload.milestone_id
    ).first()
    
    if not milestone:
        raise ResourceNotFoundException("Milestone")
    
    contract = milestone.contract
    freelancer = db.query(FreelancerProfile).filter(
        FreelancerProfile.user_id == current_user.id
    ).first()
    
    is_client = contract.client_id == current_user.id
    is_freelancer = freelancer and contract.freelancer_id == freelancer.id
    
    if not (is_client or is_freelancer):
        raise AuthorizationException("You are not authorized to delete deliverables from this milestone")
    
    FileStorageService.delete_file(file_upload, db)


@router.get("/file/{file_id}/download")
def download_file(
    file_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get download URL for file (with authorization check)"""
    logger.info(f"Requesting download URL for file: {file_id}")
    
    file_upload = db.query(FileUpload).filter(
        FileUpload.id == file_id,
        FileUpload.deleted_at == None
    ).first()
    
    if not file_upload:
        raise ResourceNotFoundException("File")
    
    # For private files, verify user has access
    if not file_upload.is_public:
        has_access = file_upload.uploaded_by_user_id == current_user.id
        
        # Profile picture owner can access
        if not has_access and file_upload.user_id:
            has_access = file_upload.user_id == current_user.id
        
        # Proposal: client or freelancer can access
        if not has_access and file_upload.proposal_id:
            proposal = db.query(Proposal).filter(
                Proposal.id == file_upload.proposal_id
            ).first()
            
            if proposal:
                if proposal.job.client_id == current_user.id:
                    has_access = True
                else:
                    freelancer = db.query(FreelancerProfile).filter(
                        FreelancerProfile.user_id == current_user.id
                    ).first()
                    if freelancer and proposal.freelancer_id == freelancer.id:
                        has_access = True
        
        # Contract: client or freelancer can access
        if not has_access and file_upload.contract_id:
            contract = db.query(Contract).filter(
                Contract.id == file_upload.contract_id
            ).first()
            
            if contract:
                if contract.client_id == current_user.id:
                    has_access = True
                else:
                    freelancer = db.query(FreelancerProfile).filter(
                        FreelancerProfile.user_id == current_user.id
                    ).first()
                    if freelancer and contract.freelancer_id == freelancer.id:
                        has_access = True
        
        # Milestone: client or freelancer can access
        if not has_access and file_upload.milestone_id:
            milestone = db.query(Milestone).filter(
                Milestone.id == file_upload.milestone_id
            ).first()
            
            if milestone:
                contract = milestone.contract
                if contract.client_id == current_user.id:
                    has_access = True
                else:
                    freelancer = db.query(FreelancerProfile).filter(
                        FreelancerProfile.user_id == current_user.id
                    ).first()
                    if freelancer and contract.freelancer_id == freelancer.id:
                        has_access = True
        
        if not has_access:
            raise AuthorizationException("You are not authorized to access this file")
    
    # Generate fresh signed URL on-demand (never return stored URL)
    download_url = FileStorageService.get_file_download_url(file_upload, expires_in_seconds=3600)
    
    return {
        "download_url": download_url,
        "filename": file_upload.original_filename,
        "expires_in_seconds": 3600
    }