import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.core.logging import get_logger
from app.models.oneroster import AcademicSession, Org, User
from app.schemas.oneroster import (
    AcademicSessionCreate, OrgCreate, UserCreate,
    EntityType
)

logger = get_logger(__name__)


class CSVProcessingService:
    """CSV処理サービス"""
    
    def __init__(self, schema_file_path: str):
        """初期化
        
        Args:
            schema_file_path: OneRoster Japan Profileスキーマファイルのパス
        """
        with open(schema_file_path, 'r', encoding='utf-8') as f:
            self.schema = json.load(f)
        
        # エンティティとモデルのマッピング
        self.entity_model_mapping = {
            EntityType.ACADEMIC_SESSIONS: AcademicSession,
            EntityType.ORGS: Org,
            EntityType.USERS: User
        }
        
        # エンティティとスキーマクラスのマッピング
        self.entity_schema_mapping = {
            EntityType.ACADEMIC_SESSIONS: AcademicSessionCreate,
            EntityType.ORGS: OrgCreate,
            EntityType.USERS: UserCreate
        }
    
    def validate_csv_structure(self, file_path: str, entity_type: EntityType) -> bool:
        """CSVファイルの構造を検証
        
        Args:
            file_path: CSVファイルのパス
            entity_type: エンティティタイプ
            
        Returns:
            bool: 検証結果
        """
        try:
            df = pd.read_csv(file_path)
            required_fields = [
                field['name'] for field in self.schema[entity_type.value]['fields']
                if field.get('required', False)
            ]
            
            missing_fields = set(required_fields) - set(df.columns)
            if missing_fields:
                logger.error(f"Missing required fields in {entity_type.value}: {missing_fields}")
                return False
            
            logger.info(f"CSV structure validation passed for {entity_type.value}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating CSV structure: {e}")
            return False
    
    def process_csv_file(
        self, 
        file_path: str, 
        entity_type: EntityType,
        db: Session
    ) -> Dict[str, Any]:
        """CSVファイルを処理してデータベースに保存
        
        Args:
            file_path: CSVファイルのパス
            entity_type: エンティティタイプ
            db: データベースセッション
            
        Returns:
            Dict: 処理結果
        """
        try:
            # CSVファイルの読み込み
            df = pd.read_csv(file_path)
            
            # 空の値をNoneに変換
            df = df.where(pd.notnull(df), None)
            
            model_class = self.entity_model_mapping[entity_type]
            schema_class = self.entity_schema_mapping[entity_type]
            
            created_count = 0
            updated_count = 0
            errors = []
            
            for index, row in df.iterrows():
                try:
                    # データの変換
                    row_data = self._convert_row_data(row.to_dict(), entity_type)
                    
                    # Pydanticスキーマでバリデーション
                    validated_data = schema_class(**row_data)
                    
                    # 既存レコードの確認
                    existing_record = db.query(model_class).filter(
                        model_class.sourcedId == validated_data.sourcedId
                    ).first()
                    
                    current_time = datetime.utcnow()
                    
                    if existing_record:
                        # 既存レコードの更新
                        for key, value in validated_data.model_dump(exclude_unset=True).items():
                            if key not in ['FirstSeenDateTime']:  # FirstSeenDateTimeは更新しない
                                setattr(existing_record, key, value)
                        
                        # LastSeenDateTimeのみ更新
                        existing_record.LastSeenDateTime = current_time
                        updated_count += 1
                        
                    else:
                        # 新規レコードの作成
                        record_data = validated_data.model_dump()
                        record_data['FirstSeenDateTime'] = current_time
                        record_data['LastSeenDateTime'] = current_time
                        
                        new_record = model_class(**record_data)
                        db.add(new_record)
                        created_count += 1
                        
                except Exception as e:
                    error_msg = f"Row {index + 1}: {str(e)}"
                    errors.append(error_msg)
                    logger.warning(error_msg)
            
            # コミット
            db.commit()
            
            result = {
                'success': True,
                'entity_type': entity_type.value,
                'created_count': created_count,
                'updated_count': updated_count,
                'total_processed': created_count + updated_count,
                'errors': errors
            }
            
            logger.info(f"CSV processing completed for {entity_type.value}: {result}")
            return result
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error processing CSV file: {e}")
            return {
                'success': False,
                'entity_type': entity_type.value,
                'error': str(e),
                'errors': [str(e)]
            }
    
    def _convert_row_data(self, row_data: Dict[str, Any], entity_type: EntityType) -> Dict[str, Any]:
        """行データを適切な型に変換
        
        Args:
            row_data: 行データ
            entity_type: エンティティタイプ
            
        Returns:
            Dict: 変換された行データ
        """
        converted_data = {}
        entity_fields = self.schema[entity_type.value]['fields']
        
        for field in entity_fields:
            field_name = field['name']
            field_type = field['type']
            value = row_data.get(field_name)
            
            if value is None or (isinstance(value, str) and value.strip() == ''):
                converted_data[field_name] = None
                continue
            
            try:
                if field_type == 'boolean':
                    if isinstance(value, str):
                        converted_data[field_name] = value.lower() in ('true', '1', 'yes', 'on')
                    else:
                        converted_data[field_name] = bool(value)
                elif field_type == 'datetime':
                    if isinstance(value, str):
                        # ISO8601形式の日時文字列をパース
                        converted_data[field_name] = pd.to_datetime(value).to_pydatetime()
                    else:
                        converted_data[field_name] = value
                elif field_type == 'date':
                    if isinstance(value, str):
                        # 日付文字列をパース
                        converted_data[field_name] = pd.to_datetime(value).date()
                    else:
                        converted_data[field_name] = value
                else:
                    converted_data[field_name] = str(value) if value is not None else None
                    
            except Exception as e:
                logger.warning(f"Error converting field {field_name}: {e}")
                converted_data[field_name] = value
        
        return converted_data
