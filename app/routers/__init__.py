from .auth import router as auth_router
from .user import router as user_router
from .contracts import router as contracts_router
from .freelancer import router as freelancer_router
from .jobs import router as jobs_router
from .milestones import router as milestones_router
from .proposals import router as proposals_router
from .reviews import router as reviews_router
from .skills import router as skills_router
from .sessions import router as Sessions_router
from .uploads import router as Uploads_router
from .notifications import router as Notification_router

__all__ = [
    "auth_router",
    "user_router",
    "contracts_router",
    "freelancer_router",
    "jobs_router",
    "milestones_router",
    "proposals_router",
    "reviews_router",
    "skills_router",
    "Sessions_router",
    "Uploads_router",
    "Notification_router"
]
