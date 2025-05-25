"""
OneRoster管理者CRUD操作エンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from app.db.database import get_db
from app.models.oneroster import User, Org, AcademicSession
from app.core.security import verify_api_key
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
async def list_users(
    limit: int = Query(default=100, ge=1, le=1000, description="取得件数制限"),
    skip: int = Query(default=0, ge=0, description="スキップ件数"),
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """全ユーザーリストを取得（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        total = db.query(func.count(User.sourcedId)).scalar()
        users = db.query(User).offset(skip).limit(limit).all()
        
        return {
            "users": [
                {
                    "sourcedId": user.sourcedId,
                    "username": user.username,
                    "givenName": user.givenName,
                    "familyName": user.familyName,
                    "email": user.email,
                    "enabledUser": user.enabledUser,
                    "status": user.status,
                    "dateLastModified": user.dateLastModified.isoformat() if user.dateLastModified else None,
                    "FirstSeenDateTime": user.FirstSeenDateTime.isoformat() if user.FirstSeenDateTime else None,
                    "LastSeenDateTime": user.LastSeenDateTime.isoformat() if user.LastSeenDateTime else None
                }
                for user in users
            ],
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logger.error(f"Error listing users: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """特定ユーザーの詳細を取得（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        user = db.query(User).filter(User.sourcedId == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "sourcedId": user.sourcedId,
            "username": user.username,
            "givenName": user.givenName,
            "familyName": user.familyName,
            "email": user.email,
            "sms": user.sms,
            "phone": user.phone,
            "enabledUser": user.enabledUser,
            "status": user.status,
            "dateLastModified": user.dateLastModified.isoformat() if user.dateLastModified else None,
            "FirstSeenDateTime": user.FirstSeenDateTime.isoformat() if user.FirstSeenDateTime else None,
            "LastSeenDateTime": user.LastSeenDateTime.isoformat() if user.LastSeenDateTime else None
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    user_data: dict,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """ユーザー情報を更新（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        user = db.query(User).filter(User.sourcedId == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # 更新可能フィールドのみ更新
        updateable_fields = ["username", "givenName", "familyName", "email", "sms", "phone", "enabledUser", "status"]
        
        for field, value in user_data.items():
            if field in updateable_fields and hasattr(user, field):
                setattr(user, field, value)
        
        db.commit()
        db.refresh(user)
        
        return {
            "message": "User updated successfully",
            "sourcedId": user.sourcedId,
            "username": user.username
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """ユーザーを削除（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        user = db.query(User).filter(User.sourcedId == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        db.delete(user)
        db.commit()
        
        return {
            "message": "User deleted successfully",
            "sourcedId": user_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/orgs")
async def list_orgs(
    limit: int = Query(default=100, ge=1, le=1000, description="取得件数制限"),
    skip: int = Query(default=0, ge=0, description="スキップ件数"),
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """全組織リストを取得（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        total = db.query(func.count(Org.sourcedId)).scalar()
        orgs = db.query(Org).offset(skip).limit(limit).all()
        
        return {
            "orgs": [
                {
                    "sourcedId": org.sourcedId,
                    "name": org.name,
                    "type": org.type,
                    "identifier": org.identifier,
                    "parent": org.parent,
                    "status": org.status,
                    "dateLastModified": org.dateLastModified.isoformat() if org.dateLastModified else None,
                    "FirstSeenDateTime": org.FirstSeenDateTime.isoformat() if org.FirstSeenDateTime else None,
                    "LastSeenDateTime": org.LastSeenDateTime.isoformat() if org.LastSeenDateTime else None
                }
                for org in orgs
            ],
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logger.error(f"Error listing orgs: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/academic-sessions")
async def list_academic_sessions(
    limit: int = Query(default=100, ge=1, le=1000, description="取得件数制限"),
    skip: int = Query(default=0, ge=0, description="スキップ件数"),
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """全学期情報リストを取得（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        total = db.query(func.count(AcademicSession.sourcedId)).scalar()
        sessions = db.query(AcademicSession).offset(skip).limit(limit).all()
        
        return {
            "academic_sessions": [
                {
                    "sourcedId": session.sourcedId,
                    "title": session.title,
                    "type": session.type,
                    "startDate": session.startDate.isoformat() if session.startDate else None,
                    "endDate": session.endDate.isoformat() if session.endDate else None,
                    "parent": session.parent,
                    "schoolYear": session.schoolYear,
                    "status": session.status,
                    "dateLastModified": session.dateLastModified.isoformat() if session.dateLastModified else None,
                    "FirstSeenDateTime": session.FirstSeenDateTime.isoformat() if session.FirstSeenDateTime else None,
                    "LastSeenDateTime": session.LastSeenDateTime.isoformat() if session.LastSeenDateTime else None
                }
                for session in sessions
            ],
            "total": total,
            "limit": limit,
            "skip": skip
        }
    except Exception as e:
        logger.error(f"Error listing academic sessions: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_system_stats(
    db: Session = Depends(get_db),
    auth_info: dict = Depends(verify_api_key)
):
    """システム統計情報を取得（管理者権限が必要）"""
    # 管理者権限チェック
    if "admin" not in auth_info.get("permissions", []):
        raise HTTPException(
            status_code=403,
            detail="Admin permission required"
        )
    
    try:
        user_count = db.query(func.count(User.sourcedId)).scalar()
        org_count = db.query(func.count(Org.sourcedId)).scalar()
        session_count = db.query(func.count(AcademicSession.sourcedId)).scalar()
        
        return {
            "stats": {
                "users": user_count,
                "orgs": org_count,
                "academic_sessions": session_count,
                "total_entities": user_count + org_count + session_count
            }
        }
    except Exception as e:
        logger.error(f"Error getting system stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
