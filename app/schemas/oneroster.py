from pydantic import BaseModel, Field
from datetime import datetime, date
from typing import Optional, List, Union
from enum import Enum


class EntityType(str, Enum):
    """OneRoster エンティティタイプ"""
    ACADEMIC_SESSIONS = "academicSessions"
    ORGS = "orgs"
    USERS = "users"


class StatusType(str, Enum):
    """OneRoster ステータスタイプ"""
    ACTIVE = "active"
    TOBEDELETED = "tobedeleted"


# Base Schemas
class OneRosterBaseSchema(BaseModel):
    """OneRoster 共通スキーマ"""
    sourcedId: str = Field(..., description="一意なID")
    status: Optional[StatusType] = Field(None, description="状態")
    dateLastModified: Optional[datetime] = Field(None, description="最終更新日時")
    FirstSeenDateTime: Optional[datetime] = Field(None, description="初回アップロード日時")
    LastSeenDateTime: Optional[datetime] = Field(None, description="最終更新日時")


# Academic Session Schemas
class AcademicSessionBase(BaseModel):
    """学期・年度等の期間情報ベーススキーマ"""
    title: str = Field(..., description="期間名")
    type: str = Field(..., description="期間種別")
    startDate: date = Field(..., description="開始日")
    endDate: date = Field(..., description="終了日")
    parent: Optional[str] = Field(None, description="親期間のsourcedId")
    schoolYear: str = Field(..., description="年度")


class AcademicSessionCreate(AcademicSessionBase):
    """学期・年度作成スキーマ"""
    sourcedId: str
    status: Optional[StatusType] = None
    dateLastModified: Optional[datetime] = None


class AcademicSessionResponse(OneRosterBaseSchema, AcademicSessionBase):
    """学期・年度レスポンススキーマ"""
    
    class Config:
        from_attributes = True


# Organization Schemas
class OrgBase(BaseModel):
    """組織情報ベーススキーマ"""
    name: str = Field(..., description="組織名")
    type: str = Field(..., description="組織種別")
    identifier: str = Field(..., description="組織コード")
    parent: Optional[str] = Field(None, description="親組織のID")


class OrgCreate(OrgBase):
    """組織作成スキーマ"""
    sourcedId: str
    status: Optional[StatusType] = None
    dateLastModified: Optional[datetime] = None


class OrgResponse(OneRosterBaseSchema, OrgBase):
    """組織レスポンススキーマ"""
    
    class Config:
        from_attributes = True


# User Schemas
class UserBase(BaseModel):
    """ユーザー情報ベーススキーマ"""
    enabledUser: bool = Field(..., description="有効ユーザーフラグ")
    username: str = Field(..., description="ログインID")
    givenName: str = Field(..., description="名")
    familyName: str = Field(..., description="姓")
    email: Optional[str] = Field(None, description="メールアドレス")
    sms: Optional[str] = Field(None, description="SMS番号")
    phone: Optional[str] = Field(None, description="電話番号")


class UserCreate(UserBase):
    """ユーザー作成スキーマ"""
    sourcedId: str
    status: Optional[StatusType] = None
    dateLastModified: Optional[datetime] = None


class UserResponse(OneRosterBaseSchema, UserBase):
    """ユーザーレスポンススキーマ"""
    
    class Config:
        from_attributes = True


# Upload Schema
class UploadResponse(BaseModel):
    """アップロードレスポンススキーマ"""
    success: bool
    message: str
    uploaded_count: dict[str, Union[int, str]]
    errors: List[str] = []


# Delta Query Schema
class DeltaQuery(BaseModel):
    """差分取得クエリスキーマ"""
    limit: Optional[int] = Field(100, ge=1, le=1000, description="取得件数制限")
    since: Optional[datetime] = Field(None, description="指定日時以降の更新データを取得")
    
    
# Generic Response Schema
class OneRosterResponse(BaseModel):
    """OneRoster API レスポンススキーマ"""
    data: List[dict]
    total: int
    limit: Optional[int] = None
    offset: Optional[int] = None
