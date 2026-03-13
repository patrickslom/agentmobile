from fastapi import APIRouter, Depends

from app.domains.admin.router import router as admin_router
from app.domains.auth.dependencies import get_current_user
from app.domains.auth.router import router as auth_router
from app.domains.bookmarks.router import router as bookmarks_router
from app.domains.chat.router import router as chat_router
from app.domains.codex.router import router as codex_router
from app.domains.files.router import router as files_router
from app.domains.files.workspace_router import router as workspace_files_router
from app.domains.heartbeat.router import router as heartbeat_router
from app.domains.locks.router import router as locks_router
from app.domains.projects.router import router as projects_router
from app.domains.settings.router import router as settings_router
from app.db.models import User

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(bookmarks_router)
api_router.include_router(codex_router)
api_router.include_router(files_router)
api_router.include_router(workspace_files_router)
api_router.include_router(heartbeat_router)
api_router.include_router(settings_router)
api_router.include_router(admin_router)
api_router.include_router(locks_router)
api_router.include_router(projects_router)


@api_router.get("/me", tags=["auth"])
def get_me(user: User = Depends(get_current_user)) -> dict[str, dict[str, str]]:
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
        }
    }
