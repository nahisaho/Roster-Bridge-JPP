import pytest


class TestAPI:
    """API基本テスト"""
    
    def test_root_endpoint(self, client):
        """ルートエンドポイントのテスト"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Roster Bridge API"
    
    def test_health_check(self, client):
        """ヘルスチェックのテスト"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_unauthorized_access(self, client):
        """認証なしアクセスのテスト"""
        response = client.get("/api/v1/users")
        assert response.status_code == 401
    
    def test_invalid_api_key(self, client):
        """無効なAPIキーのテスト"""
        headers = {"Authorization": "Bearer invalid-api-key"}
        response = client.get("/api/v1/users", headers=headers)
        assert response.status_code == 401


class TestAuthentication:
    """認証テスト"""
    
    def test_valid_api_key(self, client, api_headers):
        """有効なAPIキーのテスト"""
        response = client.get("/api/v1/users", headers=api_headers)
        # 認証は通るがデータがないので空のレスポンス
        assert response.status_code == 200
    
    def test_missing_authorization_header(self, client):
        """認証ヘッダーなしのテスト"""
        response = client.get("/api/v1/users")
        assert response.status_code == 401
