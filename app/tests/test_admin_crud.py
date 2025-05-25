"""
Admin CRUD API のテストモジュール
"""
import io
import json
import pytest
from fastapi.testclient import TestClient

class TestAdminCRUD:
    """Admin CRUD API のテストクラス"""
    
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
        
    def test_get_admin_stats(self, client, api_headers):
        """管理者統計情報の取得テスト"""
        response = client.get("/api/v1/admin/stats", headers=api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "stats" in data
        stats = data["stats"]
        assert "users" in stats
        assert "orgs" in stats
        assert "academic_sessions" in stats
        assert isinstance(stats["users"], int)
        assert isinstance(stats["orgs"], int)
        assert isinstance(stats["academic_sessions"], int)
        
    def test_get_admin_users(self, client, api_headers):
        """管理者ユーザー一覧取得テスト"""
        response = client.get("/api/v1/admin/users", headers=api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        
    def test_get_admin_users_with_pagination(self, client, api_headers):
        """管理者ユーザー一覧の改ページテスト"""
        response = client.get("/api/v1/admin/users?limit=1&skip=0", headers=api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "users" in data
        assert len(data["users"]) <= 1
        
    def test_get_admin_user_by_id(self, client, api_headers):
        """管理者特定ユーザー取得テスト"""
        # まずユーザー一覧を取得してIDを確認
        response = client.get("/api/v1/admin/users", headers=api_headers)
        assert response.status_code == 200
        
        users = response.json()["users"]
        if users:
            user_id = users[0]["sourcedId"]
            
            # 特定ユーザーを取得
            response = client.get(f"/api/v1/admin/users/{user_id}", headers=api_headers)
            assert response.status_code == 200
            
            user = response.json()
            assert user["sourcedId"] == user_id
            
    def test_get_admin_user_not_found(self, client, api_headers):
        """管理者存在しないユーザー取得テスト"""
        response = client.get("/api/v1/admin/users/non-existent-id", headers=api_headers)
        assert response.status_code == 404
        
    def test_update_admin_user(self, client, api_headers):
        """管理者ユーザー更新テスト"""
        # まずユーザー一覧を取得してIDを確認
        response = client.get("/api/v1/admin/users", headers=api_headers)
        assert response.status_code == 200
        
        users = response.json()["users"]
        if users:
            user_id = users[0]["sourcedId"]
            
            # ユーザー更新
            update_data = {
                "email": "updated@example.com"
            }
            response = client.put(
                f"/api/v1/admin/users/{user_id}",
                headers=api_headers,
                json=update_data
            )
            assert response.status_code == 200
            
            # 更新されたことを確認 - レスポンスは成功メッセージのみ
            result = response.json()
            assert "message" in result or "status" in result
            
    def test_delete_admin_user(self, client, api_headers):
        """管理者ユーザー削除テスト"""
        # まずユーザー一覧を取得してIDを確認
        response = client.get("/api/v1/admin/users", headers=api_headers)
        assert response.status_code == 200
        
        users = response.json()["users"]
        if users:
            user_id = users[0]["sourcedId"]
            
            # ユーザー削除
            response = client.delete(f"/api/v1/admin/users/{user_id}", headers=api_headers)
            assert response.status_code == 200
            
            # 削除されたことを確認
            response = client.get(f"/api/v1/admin/users/{user_id}", headers=api_headers)
            assert response.status_code == 404
            
    def test_get_admin_orgs(self, client, api_headers):
        """管理者組織一覧取得テスト"""
        response = client.get("/api/v1/admin/orgs", headers=api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "orgs" in data
        assert isinstance(data["orgs"], list)
        
    def test_get_admin_academic_sessions(self, client, api_headers):
        """管理者学期一覧取得テスト"""
        response = client.get("/api/v1/admin/academic-sessions", headers=api_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "academic_sessions" in data
        assert isinstance(data["academic_sessions"], list)
        
    def test_admin_unauthorized_access(self, client):
        """管理者権限なしでのアクセステスト"""
        # write権限のみのAPIキーを使用
        headers = {"X-API-Key": "test-api-key-67890"}
        
        response = client.get("/api/v1/admin/stats", headers=headers)
        assert response.status_code == 403
        
    def test_admin_invalid_api_key(self, client):
        """無効なAPIキーでの管理者アクセステスト"""
        headers = {"X-API-Key": "invalid-key"}
        
        response = client.get("/api/v1/admin/stats", headers=headers)
        assert response.status_code == 401
