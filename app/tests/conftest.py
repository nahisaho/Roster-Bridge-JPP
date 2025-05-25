import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.database import get_db, Base
from app.core.config import settings

# モデルをインポートしてBase.metadataに登録
from app.models.oneroster import AcademicSession, Org, User

# テスト用設定オーバーライド
settings.api_key = "test-api-key"

# テスト用データベースURL（一時ファイルベースのSQLiteを使用）
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

# テスト用エンジンとセッション
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """テスト用データベースセッション"""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


# データベース依存関係をオーバーライド
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """テストセッション開始時にデータベースセットアップ"""
    # 既存のテーブルをクリア
    Base.metadata.drop_all(bind=engine)
    # テーブルを作成
    Base.metadata.create_all(bind=engine)
    yield
    # テストセッション終了時にクリーンアップ
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function", autouse=True)
def clean_db():
    """各テスト関数の前後でデータベースをクリーンアップ"""
    # テスト前: データをクリア（テーブル構造は保持）
    db = TestingSessionLocal()
    try:
        # 全テーブルのデータを削除
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
    
    yield
    
    # テスト後: データをクリア
    db = TestingSessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture(scope="session")
def client():
    """テストクライアントのフィクスチャ"""
    return TestClient(app)

@pytest.fixture
def db_session():
    """テスト用データベースセッションのフィクスチャ"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def api_headers():
    """API認証ヘッダー"""
    return {"X-API-Key": settings.api_key}


@pytest.fixture
def sample_csv_content():
    """サンプルCSVコンテンツ"""
    return {
        "academic_sessions": """sourcedId,status,dateLastModified,title,type,startDate,endDate,parent,schoolYear
test-session-1,active,2024-04-01T00:00:00Z,2024年度,schoolYear,2024-04-01,2025-03-31,,2024""",
        
        "orgs": """sourcedId,status,dateLastModified,name,type,identifier,parent
test-org-1,active,2024-04-01T00:00:00Z,テスト学校,school,123456,""",
        
        "users": """sourcedId,status,dateLastModified,enabledUser,username,givenName,familyName,email,sms,phone
test-user-1,active,2024-04-01T00:00:00Z,true,testuser,太郎,田中,test@example.com,,090-1234-5678"""
    }


@pytest.fixture
def temp_csv_files(sample_csv_content):
    """一時CSVファイル"""
    files = {}
    temp_files = []
    
    for entity_type, content in sample_csv_content.items():
        temp_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.csv', 
            delete=False,
            encoding='utf-8'
        )
        temp_file.write(content)
        temp_file.close()
        
        files[entity_type] = temp_file.name
        temp_files.append(temp_file.name)
    
    yield files
    
    # クリーンアップ
    for temp_file in temp_files:
        if os.path.exists(temp_file):
            os.remove(temp_file)
