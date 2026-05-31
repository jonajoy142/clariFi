from fastapi import APIRouter

from app.api.routes import router as cfo_router

router = APIRouter()
router.include_router(cfo_router)
