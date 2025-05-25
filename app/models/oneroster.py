from sqlalchemy import Column, String, Boolean, DateTime, Date, Text
from sqlalchemy.sql import func
from app.db.database import Base
from datetime import datetime
from typing import Optional


class BaseModel(Base):
    """共通のベースモデル"""
    __abstract__ = True
    
    sourcedId = Column(String(255), primary_key=True, index=True)
    status = Column(String(50), nullable=True)
    dateLastModified = Column(DateTime(timezone=True), nullable=True)
    
    # OneRoster差分取得用のタイムスタンプ
    FirstSeenDateTime = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        doc="初回アップロード日時"
    )
    LastSeenDateTime = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        onupdate=func.now(),
        doc="最終更新日時"
    )


class AcademicSession(BaseModel):
    """学期・年度等の期間情報モデル"""
    __tablename__ = "academic_sessions"
    
    title = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    startDate = Column(Date, nullable=False)
    endDate = Column(Date, nullable=False)
    parent = Column(String(255), nullable=True)
    schoolYear = Column(String(10), nullable=False)


class Org(BaseModel):
    """教育機関・組織情報モデル"""
    __tablename__ = "orgs"
    
    name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False)
    identifier = Column(String(255), nullable=False)
    parent = Column(String(255), nullable=True)


class User(BaseModel):
    """ユーザー情報モデル"""
    __tablename__ = "users"
    
    enabledUser = Column(Boolean, nullable=False, default=True)
    username = Column(String(255), nullable=False, unique=True, index=True)
    givenName = Column(String(255), nullable=False)
    familyName = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    sms = Column(String(50), nullable=True)
    phone = Column(String(50), nullable=True)
