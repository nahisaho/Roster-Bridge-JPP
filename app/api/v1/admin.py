"""
APIキー管理エンドポイント
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from pydantic import BaseModel
from app.core.security import verify_api_key
from app.services.api_key_manager import api_key_manager
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class APIKeyInfo(BaseModel):
    """APIキー情報"""
    description: str
    created_at: str
    active: bool
    permissions: List[str]


class CreateAPIKeyRequest(BaseModel):
    """APIキー作成リクエスト"""
    key_name: str
    api_key: str
    description: str = ""
    permissions: List[str] = ["read"]


@router.get("/api-keys", response_model=Dict[str, APIKeyInfo])
async def get_api_keys(auth_info: dict = Depends(verify_api_key)):
    """
    全てのAPIキー情報を取得（管理者権限が必要）
    """
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        keys_info = api_key_manager.get_all_keys()
        return {
            key_name: APIKeyInfo(**key_info)
            for key_name, key_info in keys_info.items()
        }
    except Exception as e:
        logger.error(f"Error getting API keys: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/api-keys")
async def create_api_key(
    request: CreateAPIKeyRequest,
    auth_info: dict = Depends(verify_api_key)
):
    """
    新しいAPIキーを作成（管理者権限が必要）
    """
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        success = api_key_manager.add_api_key(
            key_name=request.key_name,
            api_key=request.api_key,
            description=request.description,
            permissions=request.permissions
        )
        
        if success:
            logger.info(f"New API key created: {request.key_name}")
            return {"message": "API key created successfully", "key_name": request.key_name}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to create API key"
            )
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.delete("/api-keys/{key_name}")
async def deactivate_api_key(
    key_name: str,
    auth_info: dict = Depends(verify_api_key)
):
    """
    APIキーを無効化（管理者権限が必要）
    """
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        success = api_key_manager.deactivate_api_key(key_name)
        
        if success:
            logger.info(f"API key deactivated: {key_name}")
            return {"message": "API key deactivated successfully", "key_name": key_name}
        else:
            raise HTTPException(
                status_code=404,
                detail="API key not found"
            )
    except Exception as e:
        logger.error(f"Error deactivating API key: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )


@router.post("/api-keys/reload")
async def reload_api_keys(auth_info: dict = Depends(verify_api_key)):
    """
    APIキー設定を再読み込み（管理者権限が必要）
    """
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        api_key_manager.reload_keys()
        logger.info("API keys reloaded")
        return {"message": "API keys reloaded successfully"}
    except Exception as e:
        logger.error(f"Error reloading API keys: {e}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )
