from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models.oneroster import AcademicSession, Org, User
from app.schemas.oneroster import EntityType, OneRosterResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class OneRosterAPIService:
    """OneRoster API サービス"""
    
    def __init__(self):
        """初期化"""
        self.entity_model_mapping = {
            EntityType.ACADEMIC_SESSIONS: AcademicSession,
            EntityType.ORGS: Org,
            EntityType.USERS: User
        }
    
    def get_all_entities(
        self,
        entity_type: EntityType,
        db: Session,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> OneRosterResponse:
        """全件取得API
        
        Args:
            entity_type: エンティティタイプ
            db: データベースセッション
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            OneRosterResponse: レスポンス
        """
        try:
            model_class = self.entity_model_mapping[entity_type]
            
            # ベースクエリ
            query = db.query(model_class)
            
            # 総件数の取得
            total = query.count()
            
            # ページネーション
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # データ取得
            entities = query.all()
            
            # レスポンス用データの変換
            data = [self._model_to_dict(entity) for entity in entities]
            
            logger.info(
                f"Retrieved {len(data)} {entity_type.value} entities "
                f"(total: {total}, limit: {limit}, offset: {offset})"
            )
            
            return OneRosterResponse(
                data=data,
                total=total,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error retrieving {entity_type.value} entities: {e}")
            raise
    
    def get_delta_entities(
        self,
        entity_type: EntityType,
        db: Session,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> OneRosterResponse:
        """差分取得API
        
        Args:
            entity_type: エンティティタイプ
            db: データベースセッション
            since: 指定日時以降の更新データを取得
            limit: 取得件数制限
            offset: オフセット
            
        Returns:
            OneRosterResponse: レスポンス
        """
        try:
            model_class = self.entity_model_mapping[entity_type]
            
            # ベースクエリ
            query = db.query(model_class)
            
            # 差分フィルター適用
            if since:
                query = query.filter(
                    model_class.LastSeenDateTime >= since
                )
            
            # 総件数の取得
            total = query.count()
            
            # ソート（最新更新順）
            query = query.order_by(model_class.LastSeenDateTime.desc())
            
            # ページネーション
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            # データ取得
            entities = query.all()
            
            # レスポンス用データの変換
            data = [self._model_to_dict(entity) for entity in entities]
            
            logger.info(
                f"Retrieved {len(data)} delta {entity_type.value} entities "
                f"(total: {total}, since: {since}, limit: {limit}, offset: {offset})"
            )
            
            return OneRosterResponse(
                data=data,
                total=total,
                limit=limit,
                offset=offset
            )
            
        except Exception as e:
            logger.error(f"Error retrieving delta {entity_type.value} entities: {e}")
            raise
    
    def get_entity_by_id(
        self,
        entity_type: EntityType,
        sourced_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """IDによる単体取得
        
        Args:
            entity_type: エンティティタイプ
            sourced_id: エンティティID
            db: データベースセッション
            
        Returns:
            Optional[Dict]: エンティティデータ
        """
        try:
            model_class = self.entity_model_mapping[entity_type]
            
            entity = db.query(model_class).filter(
                model_class.sourcedId == sourced_id
            ).first()
            
            if entity:
                logger.info(f"Retrieved {entity_type.value} entity: {sourced_id}")
                return self._model_to_dict(entity)
            
            logger.warning(f"{entity_type.value} entity not found: {sourced_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving {entity_type.value} entity {sourced_id}: {e}")
            raise
    
    def _model_to_dict(self, model_instance) -> Dict[str, Any]:
        """SQLAlchemyモデルインスタンスを辞書に変換
        
        Args:
            model_instance: モデルインスタンス
            
        Returns:
            Dict: 辞書形式のデータ
        """
        result = {}
        
        for column in model_instance.__table__.columns:
            value = getattr(model_instance, column.name)
            
            # datetime オブジェクトを ISO8601 文字列に変換
            if isinstance(value, datetime):
                result[column.name] = value.isoformat()
            # date オブジェクトを文字列に変換
            elif hasattr(value, 'isoformat'):
                result[column.name] = value.isoformat()
            else:
                result[column.name] = value
        
        return result
