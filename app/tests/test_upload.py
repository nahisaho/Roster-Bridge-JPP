import pytest
import io


class TestUploadAPI:
    """ファイルアップロードAPIのテスト"""
    
    def test_upload_academic_sessions_sync(self, client, api_headers, sample_csv_content):
        """学期・年度CSVファイルの同期アップロードテスト"""
        csv_content = sample_csv_content["academic_sessions"]
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {
            "academic_sessions": ("academic_sessions.csv", csv_file, "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers,
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "academicSessions" in data["uploaded_count"]
        assert data["uploaded_count"]["academicSessions"] == 1
    
    def test_upload_orgs_sync(self, client, api_headers, sample_csv_content):
        """組織CSVファイルの同期アップロードテスト"""
        csv_content = sample_csv_content["orgs"]
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {
            "orgs": ("orgs.csv", csv_file, "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers,
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "orgs" in data["uploaded_count"]
        assert data["uploaded_count"]["orgs"] == 1
    
    def test_upload_users_sync(self, client, api_headers, sample_csv_content):
        """ユーザーCSVファイルの同期アップロードテスト"""
        csv_content = sample_csv_content["users"]
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {
            "users": ("users.csv", csv_file, "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers,
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "users" in data["uploaded_count"]
        assert data["uploaded_count"]["users"] == 1
    
    def test_upload_multiple_files_sync(self, client, api_headers, sample_csv_content):
        """複数CSVファイルの同期アップロードテスト"""
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
        data = response.json()
        assert data["success"] is True
        assert len(data["uploaded_count"]) == 3
        assert all(count == 1 for count in data["uploaded_count"].values())
    
    def test_upload_without_auth(self, client, sample_csv_content):
        """認証なしでのアップロードテスト"""
        csv_content = sample_csv_content["users"]
        csv_file = io.BytesIO(csv_content.encode('utf-8'))
        
        files = {
            "users": ("users.csv", csv_file, "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            files=files
        )
        
        assert response.status_code == 401
    
    def test_upload_no_files(self, client, api_headers):
        """ファイルなしでのアップロードテスト"""
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "有効なCSVファイルがアップロードされていません" in data["error"]["detail"]
    
    def test_upload_invalid_csv_structure(self, client, api_headers):
        """無効なCSV構造のアップロードテスト"""
        invalid_csv = "invalid,csv,structure\n1,2,3"
        csv_file = io.BytesIO(invalid_csv.encode('utf-8'))
        
        files = {
            "users": ("users.csv", csv_file, "text/csv")
        }
        
        response = client.post(
            "/api/v1/upload/upload-sync",
            headers=api_headers,
            files=files
        )
        
        # バリデーションエラーが発生するが、400エラーになる可能性
        assert response.status_code in [400, 200]
        
        if response.status_code == 200:
            data = response.json()
            assert len(data["errors"]) > 0
