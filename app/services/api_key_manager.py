"""
APIキー管理サービス
"""
import json
import os
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class APIKeyManager:
    """APIキー管理クラス"""
    
    def __init__(self, key_file_path: str = "./api_keys.json"):
        """
        初期化
        
        Args:
            key_file_path: APIキー設定ファイルのパス
        """
        self.key_file_path = key_file_path
        self._keys_config = None
        self._load_keys()
    
    def _load_keys(self) -> None:
        """APIキー設定を読み込む"""
        try:
            if os.path.exists(self.key_file_path):
                with open(self.key_file_path, 'r', encoding='utf-8') as f:
                    self._keys_config = json.load(f)
            else:
                logger.warning(f"APIキーファイルが見つかりません: {self.key_file_path}")
                self._keys_config = {"keys": {}, "default_key": None}
        except Exception as e:
            logger.error(f"APIキーファイル読み込みエラー: {e}")
            self._keys_config = {"keys": {}, "default_key": None}
    
    def get_default_api_key(self) -> Optional[str]:
        """デフォルトのAPIキーを取得"""
        if not self._keys_config or "default_key" not in self._keys_config:
            return None
            
        default_key_name = self._keys_config["default_key"]
        if default_key_name and default_key_name in self._keys_config["keys"]:
            key_info = self._keys_config["keys"][default_key_name]
            if key_info.get("active", False):
                return key_info.get("key")
        
        return None
    
    def validate_api_key(self, api_key: str) -> Dict[str, any]:
        """
        APIキーを検証する
        
        Args:
            api_key: 検証するAPIキー
            
        Returns:
            検証結果とキー情報
        """
        if not self._keys_config or "keys" not in self._keys_config:
            return {"valid": False, "reason": "No keys configured"}
        
        for key_name, key_info in self._keys_config["keys"].items():
            if key_info.get("key") == api_key and key_info.get("active", False):
                return {
                    "valid": True,
                    "key_name": key_name,
                    "permissions": key_info.get("permissions", []),
                    "description": key_info.get("description", "")
                }
        
        return {"valid": False, "reason": "Invalid or inactive API key"}
    
    def get_all_keys(self) -> Dict[str, Dict]:
        """全てのAPIキー情報を取得（キー値は除外）"""
        if not self._keys_config or "keys" not in self._keys_config:
            return {}
        
        safe_keys = {}
        for key_name, key_info in self._keys_config["keys"].items():
            safe_keys[key_name] = {
                "description": key_info.get("description", ""),
                "created_at": key_info.get("created_at", ""),
                "active": key_info.get("active", False),
                "permissions": key_info.get("permissions", [])
            }
        
        return safe_keys
    
    def add_api_key(self, key_name: str, api_key: str, description: str = "", 
                   permissions: List[str] = None) -> bool:
        """
        新しいAPIキーを追加
        
        Args:
            key_name: キー名
            api_key: APIキー値
            description: 説明
            permissions: 権限リスト
            
        Returns:
            成功フラグ
        """
        if not self._keys_config:
            self._keys_config = {"keys": {}, "default_key": None}
        
        if permissions is None:
            permissions = ["read"]
        
        self._keys_config["keys"][key_name] = {
            "key": api_key,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "active": True,
            "permissions": permissions
        }
        
        # デフォルトキーが設定されていない場合、最初のキーをデフォルトに設定
        if not self._keys_config.get("default_key"):
            self._keys_config["default_key"] = key_name
        
        return self._save_keys()
    
    def deactivate_api_key(self, key_name: str) -> bool:
        """APIキーを無効化"""
        if (self._keys_config and "keys" in self._keys_config and 
            key_name in self._keys_config["keys"]):
            self._keys_config["keys"][key_name]["active"] = False
            return self._save_keys()
        return False
    
    def _save_keys(self) -> bool:
        """APIキー設定をファイルに保存"""
        try:
            with open(self.key_file_path, 'w', encoding='utf-8') as f:
                json.dump(self._keys_config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"APIキーファイル保存エラー: {e}")
            return False
    
    def reload_keys(self) -> None:
        """設定を再読み込み"""
        self._load_keys()


# グローバルインスタンス
api_key_manager = APIKeyManager()
