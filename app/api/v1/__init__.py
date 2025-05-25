from fastapi import APIRouter
from app.api.v1 import upload, oneroster, admin, admin_crud

api_router = APIRouter()

# v1 エンドポイントの登録
api_router.include_router(upload.router, prefix="/upload", tags=["upload"])
api_router.include_router(oneroster.router, tags=["oneroster"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(admin_crud.router, tags=["admin-crud"])
