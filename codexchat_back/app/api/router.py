from fastapi import APIRouter

from app.domains.admin.router import router as admin_router
from app.domains.auth.router import router as auth_router
from app.domains.chat.router import router as chat_router
from app.domains.codex.router import router as codex_router
from app.domains.files.router import router as files_router
from app.domains.locks.router import router as locks_router
from app.domains.settings.router import router as settings_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(chat_router)
api_router.include_router(codex_router)
api_router.include_router(files_router)
api_router.include_router(settings_router)
api_router.include_router(admin_router)
api_router.include_router(locks_router)
