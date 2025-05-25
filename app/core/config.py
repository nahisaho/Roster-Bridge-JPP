from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """アプリケーション設定クラス"""
    
    # 基本設定
    debug: bool = False
    log_level: str = "INFO"
    
    # API設定
    api_key: str = "default-api-key"  # フォールバック用
    api_key_file: str = "./api_keys.json"  # APIキー設定ファイルパス
    use_external_api_keys: bool = True  # 外部APIキーファイルを使用するか
    
    # データベース設定
    database_url: str = "sqlite:///./roster_bridge.db"
    
    # ファイルアップロード設定
    max_file_size_mb: int = 100
    upload_directory: str = "./uploads"
    
    # Syslog設定
    syslog_host: str = "localhost"
    syslog_port: int = 514
    syslog_facility: int = 16
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# グローバル設定インスタンス
settings = Settings()

# アップロードディレクトリが存在しない場合は作成
os.makedirs(settings.upload_directory, exist_ok=True)
