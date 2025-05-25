import pytest
import tempfile
import os
from datetime import datetime
from sqlalchemy.orm import Session
from app.services.csv_processor import CSVProcessingService
from app.schemas.oneroster import EntityType
from app.models.oneroster import AcademicSession, Org, User


class TestCSVProcessingService:
    """CSV処理サービスのテスト"""
    
    @pytest.fixture
    def csv_processor(self):
        """CSV処理サービスのフィクスチャ"""
        return CSVProcessingService(
            schema_file_path="./oneroster_japan_profile_complete_schema_recreated.json"
        )
    
    def test_validate_csv_structure_valid(self, csv_processor, temp_csv_files):
        """有効なCSV構造の検証テスト"""
        file_path = temp_csv_files["academic_sessions"]
        result = csv_processor.validate_csv_structure(
            file_path, 
            EntityType.ACADEMIC_SESSIONS
        )
        assert result is True
    
    def test_validate_csv_structure_invalid(self, csv_processor):
        """無効なCSV構造の検証テスト"""
        # 無効なCSVファイルを作成
        invalid_csv = "invalid,csv,structure\n1,2,3"
        
        with tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.csv', 
            delete=False,
            encoding='utf-8'
        ) as temp_file:
            temp_file.write(invalid_csv)
            temp_file_path = temp_file.name
        
        try:
            result = csv_processor.validate_csv_structure(
                temp_file_path,
                EntityType.USERS
            )
            assert result is False
        finally:
            os.remove(temp_file_path)
    
    def test_process_csv_file_academic_sessions(self, csv_processor, temp_csv_files, db_session):
        """学期・年度CSVファイル処理テスト"""
        file_path = temp_csv_files["academic_sessions"]
        
        result = csv_processor.process_csv_file(
            file_path,
            EntityType.ACADEMIC_SESSIONS,
            db_session
        )
        
        assert result["success"] is True
        assert result["created_count"] == 1
        assert result["updated_count"] == 0
        assert result["total_processed"] == 1
        
        # データベースに正しく保存されているか確認
        academic_session = db_session.query(AcademicSession).filter(
            AcademicSession.sourcedId == "test-session-1"
        ).first()
        
        assert academic_session is not None
        assert academic_session.title == "2024年度"
        assert academic_session.type == "schoolYear"
        assert academic_session.schoolYear == "2024"
        assert academic_session.FirstSeenDateTime is not None
        assert academic_session.LastSeenDateTime is not None
    
    def test_process_csv_file_orgs(self, csv_processor, temp_csv_files, db_session):
        """組織CSVファイル処理テスト"""
        file_path = temp_csv_files["orgs"]
        
        result = csv_processor.process_csv_file(
            file_path,
            EntityType.ORGS,
            db_session
        )
        
        assert result["success"] is True
        assert result["created_count"] == 1
        
        # データベースに正しく保存されているか確認
        org = db_session.query(Org).filter(
            Org.sourcedId == "test-org-1"
        ).first()
        
        assert org is not None
        assert org.name == "テスト学校"
        assert org.type == "school"
        assert org.identifier == "123456"
    
    def test_process_csv_file_users(self, csv_processor, temp_csv_files, db_session):
        """ユーザーCSVファイル処理テスト"""
        file_path = temp_csv_files["users"]
        
        result = csv_processor.process_csv_file(
            file_path,
            EntityType.USERS,
            db_session
        )
        
        assert result["success"] is True
        assert result["created_count"] == 1
        
        # データベースに正しく保存されているか確認
        user = db_session.query(User).filter(
            User.sourcedId == "test-user-1"
        ).first()
        
        assert user is not None
        assert user.username == "testuser"
        assert user.givenName == "太郎"
        assert user.familyName == "田中"
        assert user.enabledUser is True
        assert user.email == "test@example.com"
        assert user.phone == "090-1234-5678"
    
    def test_process_csv_file_update_existing(self, csv_processor, temp_csv_files, db_session):
        """既存レコード更新テスト"""
        file_path = temp_csv_files["users"]
        
        # 初回処理
        result1 = csv_processor.process_csv_file(
            file_path,
            EntityType.USERS,
            db_session
        )
        assert result1["created_count"] == 1
        assert result1["updated_count"] == 0
        
        # 初回作成時のタイムスタンプを取得
        user = db_session.query(User).filter(
            User.sourcedId == "test-user-1"
        ).first()
        first_seen = user.FirstSeenDateTime
        
        # 同じファイルを再度処理（更新）
        result2 = csv_processor.process_csv_file(
            file_path,
            EntityType.USERS,
            db_session
        )
        assert result2["created_count"] == 0
        assert result2["updated_count"] == 1
        
        # FirstSeenDateTimeは変更されず、LastSeenDateTimeが更新されることを確認
        user_updated = db_session.query(User).filter(
            User.sourcedId == "test-user-1"
        ).first()
        assert user_updated.FirstSeenDateTime == first_seen
        assert user_updated.LastSeenDateTime > first_seen
