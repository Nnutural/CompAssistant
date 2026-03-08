from fastapi import APIRouter

from app.api.routes import competitions, research_runtime

api_router = APIRouter()
api_router.include_router(competitions.router, tags=["competitions"])
api_router.include_router(research_runtime.router, tags=["research-runtime"])