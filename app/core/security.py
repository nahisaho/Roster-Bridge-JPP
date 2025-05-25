from fastapi import HTTPException, Header
from typing import Optional
from app.core.config import settings
from app.core.logging import get_logger
from app.services.api_key_manager import api_key_manager

logger = get_logger(__name__)


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> dict:
    """API キーの検証"""
    
    if not x_api_key:
        logger.warning("Missing API key")
        raise HTTPException(
            status_code=401,
            detail="Missing API key"
        )
    
    # 外部APIキーファイルを使用する場合
    if settings.use_external_api_keys:
        validation_result = api_key_manager.validate_api_key(x_api_key)
        if not validation_result["valid"]:
            logger.warning(f"Invalid API key attempt: {x_api_key[:10]}... - {validation_result['reason']}")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        logger.info(f"API key verified successfully for: {validation_result['key_name']}")
        return validation_result
    
    # フォールバック: 環境変数のAPIキーをチェック
    if x_api_key != settings.api_key:
        logger.warning(f"Invalid API key attempt: {x_api_key[:10]}...")
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    
    logger.info("API key verified successfully (fallback)")
    return {"valid": True, "key_name": "environment", "permissions": ["read", "write", "admin"]}
