from fastapi import APIRouter

from app.api.v1 import auth
from app.api.v1 import users
from app.api.v1 import videos
from app.api.v1 import webhooks
from app.api.v1 import extractions
from app.api.v1 import logs

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(videos.router, prefix="/videos", tags=["videos"])
api_router.include_router(extractions.router, prefix="/extractions", tags=["extractions"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(logs.router, prefix="/logs", tags=["logs"])
