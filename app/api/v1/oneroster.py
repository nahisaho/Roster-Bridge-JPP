from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import verify_api_key
from app.core.logging import get_logger
from app.services.oneroster_api import OneRosterAPIService
from app.schemas.oneroster import EntityType, OneRosterResponse, DeltaQuery

logger = get_logger(__name__)
router = APIRouter()

# OneRoster APIサービスの初期化
oneroster_service = OneRosterAPIService()


@router.get("/academicSessions", response_model=OneRosterResponse)
async def get_academic_sessions(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """学期・年度等の期間情報全件取得API
    
    Args:
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: 期間情報一覧
    """
    try:
        result = oneroster_service.get_all_entities(
            EntityType.ACADEMIC_SESSIONS,
            db,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving academic sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/academicSessions/delta", response_model=OneRosterResponse)
async def get_academic_sessions_delta(
    since: Optional[datetime] = Query(None, description="指定日時以降の更新データを取得"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """学期・年度等の期間情報差分取得API
    
    Args:
        since: 指定日時以降の更新データを取得
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: 期間情報差分一覧
    """
    try:
        result = oneroster_service.get_delta_entities(
            EntityType.ACADEMIC_SESSIONS,
            db,
            since=since,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving academic sessions delta: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/academicSessions/{sourced_id}")
async def get_academic_session(
    sourced_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """学期・年度等の期間情報単体取得API
    
    Args:
        sourced_id: 期間情報ID
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        Dict: 期間情報
    """
    try:
        result = oneroster_service.get_entity_by_id(
            EntityType.ACADEMIC_SESSIONS,
            sourced_id,
            db
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Academic session not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving academic session {sourced_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orgs", response_model=OneRosterResponse)
async def get_orgs(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """教育機関・組織情報全件取得API
    
    Args:
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: 組織情報一覧
    """
    try:
        result = oneroster_service.get_all_entities(
            EntityType.ORGS,
            db,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving orgs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orgs/delta", response_model=OneRosterResponse)
async def get_orgs_delta(
    since: Optional[datetime] = Query(None, description="指定日時以降の更新データを取得"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """教育機関・組織情報差分取得API
    
    Args:
        since: 指定日時以降の更新データを取得
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: 組織情報差分一覧
    """
    try:
        result = oneroster_service.get_delta_entities(
            EntityType.ORGS,
            db,
            since=since,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving orgs delta: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orgs/{sourced_id}")
async def get_org(
    sourced_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """教育機関・組織情報単体取得API
    
    Args:
        sourced_id: 組織情報ID
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        Dict: 組織情報
    """
    try:
        result = oneroster_service.get_entity_by_id(
            EntityType.ORGS,
            sourced_id,
            db
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="Organization not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving org {sourced_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users", response_model=OneRosterResponse)
async def get_users(
    limit: Optional[int] = Query(None, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """ユーザー情報全件取得API
    
    Args:
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: ユーザー情報一覧
    """
    try:
        result = oneroster_service.get_all_entities(
            EntityType.USERS,
            db,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/delta", response_model=OneRosterResponse)
async def get_users_delta(
    since: Optional[datetime] = Query(None, description="指定日時以降の更新データを取得"),
    limit: Optional[int] = Query(100, ge=1, le=1000, description="取得件数制限"),
    offset: Optional[int] = Query(None, ge=0, description="オフセット"),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """ユーザー情報差分取得API
    
    Args:
        since: 指定日時以降の更新データを取得
        limit: 取得件数制限
        offset: オフセット
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        OneRosterResponse: ユーザー情報差分一覧
    """
    try:
        result = oneroster_service.get_delta_entities(
            EntityType.USERS,
            db,
            since=since,
            limit=limit,
            offset=offset
        )
        return result
    except Exception as e:
        logger.error(f"Error retrieving users delta: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{sourced_id}")
async def get_user(
    sourced_id: str,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """ユーザー情報単体取得API
    
    Args:
        sourced_id: ユーザー情報ID
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        Dict: ユーザー情報
    """
    try:
        result = oneroster_service.get_entity_by_id(
            EntityType.USERS,
            sourced_id,
            db
        )
        
        if not result:
            raise HTTPException(status_code=404, detail="User not found")
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving user {sourced_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
