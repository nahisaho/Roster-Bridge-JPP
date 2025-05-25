import pytest
import io
from datetime import datetime, timedelta


class TestOneRosterAPI:
    """OneRoster APIのテスト"""
    
    @pytest.fixture(autouse=True)
    def setup_test_data(self, client, api_headers, sample_csv_content):
        """テストデータのセットアップ"""
        # テストデータをアップロード
        files = {}
        for entity_type, content in sample_csv_content.items():
            csv_file = io.BytesIO(content.encode('utf-8'))
            files[entity_type] = (f"{entity_type}.csv", csv_file, "text/csv")
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers,
            files=files
        )
        assert response.status_code == 200
    
    def test_get_academic_sessions(self, client, api_headers):
        """学期・年度情報全件取得テスト"""
        response = client.get("/api/v1/academicSessions", headers=api_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] >= 1
        assert len(data["data"]) >= 1
        
        # データ構造の確認
        academic_session = data["data"][0]
        assert "sourcedId" in academic_session
        assert "title" in academic_session
        assert "type" in academic_session
        assert "FirstSeenDateTime" in academic_session
        assert "LastSeenDateTime" in academic_session
    
    def test_get_academic_sessions_with_pagination(self, client, api_headers):
        """学期・年度情報ページネーション取得テスト"""
        response = client.get(
            "/api/v1/academicSessions?limit=1&offset=0",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["data"]) <= 1
    
    def test_get_academic_session_by_id(self, client, api_headers):
        """学期・年度情報単体取得テスト"""
        response = client.get(
            "/api/v1/academicSessions/test-session-1",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sourcedId"] == "test-session-1"
        assert data["title"] == "2024年度"
    
    def test_get_academic_session_not_found(self, client, api_headers):
        """存在しない学期・年度情報取得テスト"""
        response = client.get(
            "/api/v1/academicSessions/non-existing-id",
            headers=api_headers
        )
        
        assert response.status_code == 404
    
    def test_get_academic_sessions_delta(self, client, api_headers):
        """学期・年度情報差分取得テスト"""
        # 過去の日時を指定
        since = (datetime.utcnow() - timedelta(hours=1)).isoformat()
        
        response = client.get(
            f"/api/v1/academicSessions/delta?since={since}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
    
    def test_get_orgs(self, client, api_headers):
        """組織情報全件取得テスト"""
        response = client.get("/api/v1/orgs", headers=api_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] >= 1
        
        # データ構造の確認
        org = data["data"][0]
        assert "sourcedId" in org
        assert "name" in org
        assert "type" in org
        assert "identifier" in org
    
    def test_get_org_by_id(self, client, api_headers):
        """組織情報単体取得テスト"""
        response = client.get("/api/v1/orgs/test-org-1", headers=api_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["sourcedId"] == "test-org-1"
        assert data["name"] == "テスト学校"
        assert data["type"] == "school"
    
    def test_get_users(self, client, api_headers):
        """ユーザー情報全件取得テスト"""
        response = client.get("/api/v1/users", headers=api_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert data["total"] >= 1
        
        # データ構造の確認
        user = data["data"][0]
        assert "sourcedId" in user
        assert "username" in user
        assert "givenName" in user
        assert "familyName" in user
        assert "enabledUser" in user
    
    def test_get_user_by_id(self, client, api_headers):
        """ユーザー情報単体取得テスト"""
        response = client.get("/api/v1/users/test-user-1", headers=api_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert data["sourcedId"] == "test-user-1"
        assert data["username"] == "testuser"
        assert data["givenName"] == "太郎"
        assert data["familyName"] == "田中"
        assert data["enabledUser"] is True
    
    def test_get_users_delta_with_since(self, client, api_headers):
        """ユーザー情報差分取得（since指定）テスト"""
        # 未来の日時を指定（差分なしのケース）
        since = (datetime.utcnow() + timedelta(hours=1)).isoformat()
        
        response = client.get(
            f"/api/v1/users/delta?since={since}",
            headers=api_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["data"]) == 0
    
    def test_unauthorized_access_to_entities(self, client):
        """認証なしでのエンティティアクセステスト"""
        endpoints = [
            "/api/v1/academicSessions",
            "/api/v1/orgs", 
            "/api/v1/users"
        ]
        
        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 401
