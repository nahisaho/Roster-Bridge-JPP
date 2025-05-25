# セキュリティハードニングガイド

このガイドでは、Roster Bridge JPP アプリケーションの Azure デプロイにおけるセキュリティ強化方法を説明します。

## 目次

1. [ネットワークセキュリティ](#ネットワークセキュリティ)
2. [認証とアクセス制御](#認証とアクセス制御)
3. [データ保護](#データ保護)
4. [アプリケーションレベルセキュリティ](#アプリケーションレベルセキュリティ)
5. [コンプライアンス](#コンプライアンス)
6. [セキュリティ監視](#セキュリティ監視)
7. [脆弱性管理](#脆弱性管理)

## ネットワークセキュリティ

### 1. Virtual Network の設定

```bash
# VNet の作成
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name "vnet-roster-bridge" \
  --address-prefix 10.0.0.0/16 \
  --subnet-name "subnet-app" \
  --subnet-prefix 10.0.1.0/24

# プライベートサブネットの作成
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name "vnet-roster-bridge" \
  --name "subnet-db" \
  --address-prefix 10.0.2.0/24
```

### 2. Network Security Group (NSG) の設定

```bash
# NSG の作成
az network nsg create \
  --resource-group $RESOURCE_GROUP \
  --name "nsg-roster-bridge-app"

# HTTPS トラフィックのみ許可
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name "nsg-roster-bridge-app" \
  --name "Allow-HTTPS" \
  --priority 100 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 443

# HTTP を HTTPS にリダイレクト用
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name "nsg-roster-bridge-app" \
  --name "Allow-HTTP-Redirect" \
  --priority 110 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes "*" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 80

# SSH アクセスを特定 IP から制限
az network nsg rule create \
  --resource-group $RESOURCE_GROUP \
  --nsg-name "nsg-roster-bridge-app" \
  --name "Allow-SSH-Admin" \
  --priority 120 \
  --direction Inbound \
  --access Allow \
  --protocol Tcp \
  --source-address-prefixes "YOUR_ADMIN_IP" \
  --source-port-ranges "*" \
  --destination-address-prefixes "*" \
  --destination-port-ranges 22
```

### 3. Private Link の設定

```bash
# データベース用プライベートエンドポイント
az network private-endpoint create \
  --resource-group $RESOURCE_GROUP \
  --name "pe-roster-bridge-db" \
  --vnet-name "vnet-roster-bridge" \
  --subnet "subnet-db" \
  --private-connection-resource-id $DB_SERVER_ID \
  --group-id postgresqlServer \
  --connection-name "roster-bridge-db-connection"

# Container Registry 用プライベートエンドポイント
az network private-endpoint create \
  --resource-group $RESOURCE_GROUP \
  --name "pe-roster-bridge-acr" \
  --vnet-name "vnet-roster-bridge" \
  --subnet "subnet-app" \
  --private-connection-resource-id $ACR_ID \
  --group-id registry \
  --connection-name "roster-bridge-acr-connection"
```

## 認証とアクセス制御

### 1. Azure Active Directory 統合

```bash
# Managed Identity の有効化
az containerapp identity assign \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --system-assigned

# AAD アプリケーション登録
az ad app create \
  --display-name "Roster Bridge JPP" \
  --sign-in-audience AzureADMyOrg \
  --web-redirect-uris "https://$APP_NAME.azurecontainerapps.io/auth/callback"
```

### 2. Role-Based Access Control (RBAC)

```bash
# カスタムロールの作成
az role definition create --role-definition '{
  "Name": "Roster Bridge Admin",
  "Description": "Can manage Roster Bridge application",
  "Actions": [
    "Microsoft.App/containerApps/read",
    "Microsoft.App/containerApps/write",
    "Microsoft.KeyVault/vaults/secrets/read",
    "Microsoft.DBforPostgreSQL/flexibleServers/read"
  ],
  "AssignableScopes": ["/subscriptions/YOUR_SUBSCRIPTION_ID/resourceGroups/'$RESOURCE_GROUP'"]
}'

# ロールの割り当て
az role assignment create \
  --assignee "user@domain.com" \
  --role "Roster Bridge Admin" \
  --resource-group $RESOURCE_GROUP
```

### 3. Multi-Factor Authentication (MFA)

```bash
# Conditional Access ポリシーの作成（Azure AD Premium 必要）
# Azure Portal で設定:
# 1. Azure AD > セキュリティ > 条件付きアクセス
# 2. 新しいポリシーを作成
# 3. 対象ユーザー: Roster Bridge 管理者
# 4. 条件: Roster Bridge アプリケーション
# 5. アクセス制御: MFA を要求
```

## データ保護

### 1. 暗号化設定

```bash
# Key Vault での顧客管理キー
az keyvault key create \
  --vault-name "${APP_NAME}-kv" \
  --name "roster-bridge-encryption-key" \
  --kty RSA \
  --size 2048

# データベース暗号化
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --backup-retention 30 \
  --geo-redundant-backup Enabled
```

### 2. Transparent Data Encryption (TDE)

```bash
# PostgreSQL の TDE 設定（自動有効）
az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --query "backup.geoRedundantBackup"
```

### 3. データ分類とラベリング

```sql
-- データベースレベルでの機密データ分類
-- PostgreSQL での実装例
CREATE POLICY row_security_policy ON users
    FOR ALL TO application_role
    USING (user_id = current_setting('app.current_user_id')::uuid);

ALTER TABLE users ENABLE ROW LEVEL SECURITY;
```

## アプリケーションレベルセキュリティ

### 1. API セキュリティ強化

```python
# app/core/security.py の強化
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import jwt

class EnhancedAPIKeySecurity:
    def __init__(self):
        self.failed_attempts = {}
        self.rate_limit_window = timedelta(minutes=15)
        self.max_attempts = 5
    
    def validate_api_key_with_rate_limiting(self, api_key: str, client_ip: str) -> dict:
        """レート制限付きAPI キー検証"""
        # レート制限チェック
        if self.is_rate_limited(client_ip):
            raise HTTPException(
                status_code=429,
                detail="Too many failed attempts. Try again later."
            )
        
        # API キー検証
        result = self.validate_api_key(api_key)
        
        if not result["valid"]:
            self.record_failed_attempt(client_ip)
            
        return result
    
    def is_rate_limited(self, client_ip: str) -> bool:
        """レート制限チェック"""
        if client_ip not in self.failed_attempts:
            return False
            
        attempts = self.failed_attempts[client_ip]
        recent_attempts = [
            timestamp for timestamp in attempts
            if datetime.now() - timestamp < self.rate_limit_window
        ]
        
        return len(recent_attempts) >= self.max_attempts
```

### 2. CORS 設定の強化

```python
# app/main.py での CORS 設定
from fastapi.middleware.cors import CORSMiddleware

# 本番環境用の厳密な CORS 設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://*.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)
```

### 3. Input Validation 強化

```python
# app/schemas/validation.py
from pydantic import BaseModel, validator, Field
import re

class SecureFileUpload(BaseModel):
    filename: str = Field(..., max_length=255)
    content_type: str
    
    @validator('filename')
    def validate_filename(cls, v):
        # ファイル名のサニタイズ
        if not re.match(r'^[a-zA-Z0-9._-]+$', v):
            raise ValueError('Invalid filename format')
        if v.startswith('.'):
            raise ValueError('Hidden files not allowed')
        return v
    
    @validator('content_type')
    def validate_content_type(cls, v):
        allowed_types = ['text/csv', 'application/csv']
        if v not in allowed_types:
            raise ValueError('Unsupported file type')
        return v
```

## コンプライアンス

### 1. GDPR コンプライアンス

```python
# app/services/gdpr_compliance.py
class GDPRComplianceService:
    def anonymize_personal_data(self, user_id: str):
        """個人データの匿名化"""
        # 個人識別情報の削除・匿名化
        pass
    
    def export_user_data(self, user_id: str) -> dict:
        """データポータビリティ（データエクスポート）"""
        pass
    
    def delete_user_data(self, user_id: str):
        """忘れられる権利（データ削除）"""
        pass
```

### 2. 監査ログの実装

```python
# app/services/audit_logger.py
import json
from datetime import datetime
from app.core.logging import get_logger

class AuditLogger:
    def __init__(self):
        self.logger = get_logger("audit")
    
    def log_data_access(self, user_id: str, resource: str, action: str):
        """データアクセスログ"""
        audit_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "ip_address": "client_ip",  # リクエストから取得
            "user_agent": "user_agent"  # リクエストから取得
        }
        self.logger.info(f"AUDIT: {json.dumps(audit_event)}")
```

## セキュリティ監視

### 1. Azure Security Center の設定

```bash
# Security Center の有効化
az security pricing create \
  --name VirtualMachines \
  --tier Standard

az security pricing create \
  --name SqlServers \
  --tier Standard

az security pricing create \
  --name AppServices \
  --tier Standard
```

### 2. セキュリティアラートの設定

```bash
# 異常なログインアクティビティアラート
az monitor scheduled-query create \
  --resource-group $RESOURCE_GROUP \
  --name "suspicious-login-activity" \
  --scopes $CONTAINER_APP_ID \
  --condition-query "
    ContainerAppConsoleLogs_CL 
    | where Log_s contains 'FAILED_LOGIN' 
    | summarize count() by bin(TimeGenerated, 5m), tostring(split(Log_s, '|')[1])
    | where count_ > 10
  " \
  --condition-threshold 1 \
  --condition-operator "GreaterThan" \
  --evaluation-frequency 5m \
  --window-size 5m \
  --severity 1 \
  --description "同一IPから短時間に多数のログイン失敗" \
  --action-groups $ACTION_GROUP_ID

# 権限昇格の検出
az monitor scheduled-query create \
  --resource-group $RESOURCE_GROUP \
  --name "privilege-escalation" \
  --scopes $CONTAINER_APP_ID \
  --condition-query "
    ContainerAppConsoleLogs_CL 
    | where Log_s contains 'PRIVILEGE_CHANGE' or Log_s contains 'ADMIN_ACCESS'
    | summarize count() by bin(TimeGenerated, 1h)
  " \
  --condition-threshold 1 \
  --condition-operator "GreaterThan" \
  --evaluation-frequency 15m \
  --window-size 1h \
  --severity 1 \
  --description "権限昇格の可能性を検出" \
  --action-groups $ACTION_GROUP_ID
```

### 3. Application Insights でのセキュリティメトリクス

```bash
# カスタムメトリクスの作成
az monitor metrics alert create \
  --name "failed-authentication-rate" \
  --resource-group $RESOURCE_GROUP \
  --scopes $APP_INSIGHTS_ID \
  --condition "avg customMetrics/failed_auth_rate > 10" \
  --window-size 5m \
  --evaluation-frequency 1m \
  --severity 2 \
  --description "認証失敗率が異常に高い" \
  --action $ACTION_GROUP_ID
```

## 脆弱性管理

### 1. Container イメージの脆弱性スキャン

```bash
# Azure Defender for container registries の有効化
az security pricing create \
  --name ContainerRegistry \
  --tier Standard

# Trivy を使用したローカルスキャン
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image $ACR_LOGIN_SERVER/roster-bridge-jpp:latest
```

### 2. 依存関係の脆弱性管理

```bash
# requirements.txt の脆弱性チェック
pip install safety
safety check -r requirements.txt

# package.json がある場合の npm audit
npm audit --audit-level high
```

### 3. コードの静的解析

```yaml
# .github/workflows/security-scan.yml
name: Security Scan

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Run Bandit Security Scan
      uses: gaurav-nelson/bandit-action@v1
      with:
        path: "app/"
        level: high
        confidence: high
        
    - name: Run Safety Check
      run: |
        pip install safety
        safety check -r requirements.txt
        
    - name: Container Security Scan
      uses: azure/container-scan@v0
      with:
        image-name: ${{ env.ACR_LOGIN_SERVER }}/roster-bridge-jpp:latest
```

## 定期的なセキュリティレビュー

### 1. 月次セキュリティチェックリスト

```bash
#!/bin/bash
# scripts/monthly-security-review.sh

echo "=== 月次セキュリティレビュー ==="

# 1. アクセスキーのローテーション確認
az keyvault secret list --vault-name "${APP_NAME}-kv" --query "[].{Name:name, Updated:attributes.updated}"

# 2. 未使用リソースの確認
az resource list --resource-group $RESOURCE_GROUP --query "[?tags.environment=='prod']"

# 3. ファイアウォールルールの確認
az postgres flexible-server firewall-rule list --resource-group $RESOURCE_GROUP --name $DB_SERVER_NAME

# 4. セキュリティアラートの確認
az security alert list --resource-group $RESOURCE_GROUP

# 5. バックアップ状態の確認
az backup vault backup-status show --resource-group $RESOURCE_GROUP

echo "=== セキュリティレビュー完了 ==="
```

### 2. 年次ペネトレーションテスト

```markdown
## ペネトレーションテスト計画

### テスト範囲
- ウェブアプリケーションの脆弱性
- API エンドポイントのセキュリティ
- 認証・認可の仕組み
- ネットワークレベルのセキュリティ

### テストツール
- OWASP ZAP
- Burp Suite
- Nessus
- Azure Security Center

### 実施頻度
- 年1回の包括的テスト
- 四半期ごとの軽度なスキャン
- 重大な変更時の追加テスト
```

## セキュリティインシデント対応

### 1. インシデント対応手順

```bash
# scripts/incident-response.sh
#!/bin/bash

INCIDENT_TYPE=$1
SEVERITY=$2

case $INCIDENT_TYPE in
  "data-breach")
    echo "データ漏洩インシデント対応を開始"
    # 1. アプリケーションの緊急停止
    az containerapp revision deactivate --name $APP_NAME --resource-group $RESOURCE_GROUP
    
    # 2. ネットワークアクセスの遮断
    az network nsg rule update --resource-group $RESOURCE_GROUP --nsg-name "nsg-roster-bridge-app" --name "DenyAll" --access Deny
    
    # 3. ログの保全
    az monitor log-analytics query --workspace $LOG_ANALYTICS_WORKSPACE --analytics-query "ContainerAppConsoleLogs_CL | where TimeGenerated > ago(24h)"
    ;;
    
  "unauthorized-access")
    echo "不正アクセスインシデント対応を開始"
    # API キーの無効化
    az keyvault secret set --vault-name "${APP_NAME}-kv" --name "api-key" --value "REVOKED-$(date +%s)"
    ;;
esac
```

### 2. 復旧手順

```bash
# scripts/recovery-procedure.sh
#!/bin/bash

echo "=== システム復旧手順 ==="

# 1. セキュリティパッチの適用
echo "セキュリティパッチを適用中..."
docker build -t $ACR_LOGIN_SERVER/roster-bridge-jpp:hotfix-$(date +%Y%m%d) .
docker push $ACR_LOGIN_SERVER/roster-bridge-jpp:hotfix-$(date +%Y%m%d)

# 2. 新しいAPI キーの生成
NEW_API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
az keyvault secret set --vault-name "${APP_NAME}-kv" --name "api-key" --value $NEW_API_KEY

# 3. アプリケーションの段階的復旧
az containerapp revision activate --name $APP_NAME --resource-group $RESOURCE_GROUP

# 4. 監視の強化
./scripts/setup-monitoring.sh $RESOURCE_GROUP $APP_NAME

echo "=== 復旧完了 ==="
```

## まとめ

このセキュリティハードニングガイドに従うことで、Roster Bridge JPP アプリケーションの Azure デプロイにおけるセキュリティレベルを大幅に向上させることができます。

重要なポイント：

1. **多層防御**: ネットワーク、アプリケーション、データの各レイヤーでセキュリティ対策を実装
2. **継続的監視**: リアルタイムでの脅威検出とアラート設定
3. **定期的レビュー**: セキュリティ設定の定期的な見直しと更新
4. **インシデント対応**: 迅速な対応と復旧のための準備
5. **コンプライアンス**: 法的要件への準拠

セキュリティは継続的なプロセスです。定期的にこのガイドを見直し、最新の脅威と対策を反映させることが重要です。
