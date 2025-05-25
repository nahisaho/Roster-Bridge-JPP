# Azure デプロイメントガイド

このガイドでは、Roster Bridge JPP アプリケーションを Microsoft Azure にデプロイする方法を説明します。

## 目次

1. [前提条件](#前提条件)
2. [Azure リソースの準備](#azure-リソースの準備)
3. [データベースのセットアップ](#データベースのセットアップ)
4. [コンテナレジストリの設定](#コンテナレジストリの設定)
5. [アプリケーションのデプロイ](#アプリケーションのデプロイ)
6. [環境変数の設定](#環境変数の設定)
7. [SSL/TLS の設定](#ssltls-の設定)
8. [監視とログ](#監視とログ)
9. [スケーリング](#スケーリング)
10. [セキュリティ設定](#セキュリティ設定)
11. [バックアップ戦略](#バックアップ戦略)
12. [継続的デプロイメント](#継続的デプロイメント)
13. [性能最適化](#性能最適化)
14. [運用・メンテナンス](#運用メンテナンス)
15. [コスト最適化](#コスト最適化)
16. [トラブルシューティング](#トラブルシューティング)

## クイックスタート

### 自動デプロイメント（推奨）

最も簡単な方法は、提供されている自動化スクリプトを使用することです：

```bash
# 本番環境へのデプロイ
./scripts/deploy-to-azure.sh prod roster-bridge-jpp japaneast

# ステージング環境へのデプロイ
./scripts/deploy-to-azure.sh staging roster-bridge-jpp japaneast
```

このスクリプトは以下の作業を自動で実行します：
- 前提条件のチェック
- Azure リソースの作成
- Docker イメージのビルドとプッシュ
- アプリケーションのデプロイ
- 監視設定
- ヘルスチェック

### 運用管理スクリプト

デプロイ後の運用管理には以下のスクリプトを使用できます：

```bash
# システム状態確認
./scripts/maintenance.sh status

# ヘルスチェック実行
./scripts/maintenance.sh health

# ログ収集と分析
./scripts/maintenance.sh logs

# バックアップ実行
./scripts/maintenance.sh backup

# コスト最適化
./scripts/cost-optimization.sh rg-roster-bridge-prod prod
```

## 前提条件

### 必要なツール

1. **Azure CLI** のインストール
```bash
# Ubuntu/Debian
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# macOS
brew install azure-cli

# Windows
# https://docs.microsoft.com/en-us/cli/azure/install-azure-cli-windows
```

2. **Docker** のインストール（ローカルビルド用）
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install docker.io docker-compose

# macOS
brew install docker docker-compose
```

3. **Azure サブスクリプション**
   - 有効な Azure サブスクリプションが必要です
   - 適切な権限（Contributor 以上）が必要です

### Azure CLI ログイン

```bash
# Azure にログイン
az login

# サブスクリプションの確認
az account show

# 必要に応じてサブスクリプションを設定
az account set --subscription "your-subscription-id"
```

## Azure リソースの準備

### 1. リソースグループの作成

```bash
# 環境変数の設定
export RESOURCE_GROUP="rg-roster-bridge-prod"
export LOCATION="japaneast"
export APP_NAME="roster-bridge-jpp"

# リソースグループの作成
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### 2. Virtual Network の作成（推奨）

```bash
# VNet の作成
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name vnet-roster-bridge \
  --address-prefix 10.0.0.0/16 \
  --subnet-name subnet-app \
  --subnet-prefix 10.0.1.0/24

# データベース用サブネットの作成
az network vnet subnet create \
  --resource-group $RESOURCE_GROUP \
  --vnet-name vnet-roster-bridge \
  --name subnet-db \
  --address-prefix 10.0.2.0/24
```

## データベースのセットアップ

### Azure Database for PostgreSQL の作成

```bash
# 環境変数の設定
export DB_SERVER_NAME="${APP_NAME}-db-server"
export DB_NAME="roster_bridge"
export DB_ADMIN_USER="rosteradmin"
export DB_ADMIN_PASSWORD="YourSecurePassword123!"

# PostgreSQL サーバーの作成（Flexible Server）
az postgres flexible-server create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --location $LOCATION \
  --admin-user $DB_ADMIN_USER \
  --admin-password $DB_ADMIN_PASSWORD \
  --version 15 \
  --sku-name Standard_B1ms \
  --tier Burstable \
  --storage-size 32 \
  --public-access 0.0.0.0-255.255.255.255

# データベースの作成
az postgres flexible-server db create \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER_NAME \
  --database-name $DB_NAME
```

### データベース接続文字列の取得

```bash
# 接続文字列の表示
echo "DATABASE_URL=postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"
```

## コンテナレジストリの設定

### Azure Container Registry の作成

```bash
export ACR_NAME="${APP_NAME}acr"

# Container Registry の作成
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku Basic \
  --admin-enabled true

# ACR にログイン
az acr login --name $ACR_NAME
```

### Docker イメージのビルドとプッシュ

```bash
# ACR ログインサーバーの取得
export ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv)

# Docker イメージのビルド
docker build -t $ACR_LOGIN_SERVER/roster-bridge-jpp:latest .

# イメージのプッシュ
docker push $ACR_LOGIN_SERVER/roster-bridge-jpp:latest
```

## アプリケーションのデプロイ

### オプション 1: Azure Container Instances

```bash
# ACR の認証情報を取得
export ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query "username" --output tsv)
export ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)

# Container Instance の作成
az container create \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --image $ACR_LOGIN_SERVER/roster-bridge-jpp:latest \
  --registry-login-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --dns-name-label $APP_NAME \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require" \
    DEBUG=False \
    LOG_LEVEL=INFO \
    API_KEY=your-production-api-key \
    USE_EXTERNAL_API_KEYS=True \
  --cpu 1 \
  --memory 2
```

### オプション 2: Azure App Service

```bash
# App Service Plan の作成
az appservice plan create \
  --name "${APP_NAME}-plan" \
  --resource-group $RESOURCE_GROUP \
  --sku B1 \
  --is-linux

# Web App の作成
az webapp create \
  --resource-group $RESOURCE_GROUP \
  --plan "${APP_NAME}-plan" \
  --name $APP_NAME \
  --deployment-container-image-name $ACR_LOGIN_SERVER/roster-bridge-jpp:latest

# ACR の認証情報を Web App に設定
az webapp config container set \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --docker-custom-image-name $ACR_LOGIN_SERVER/roster-bridge-jpp:latest \
  --docker-registry-server-url https://$ACR_LOGIN_SERVER \
  --docker-registry-server-user $ACR_USERNAME \
  --docker-registry-server-password $ACR_PASSWORD
```

### オプション 3: Azure Container Apps（推奨）

```bash
# Container Apps 環境の作成
az containerapp env create \
  --name "${APP_NAME}-env" \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Container App の作成
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment "${APP_NAME}-env" \
  --image $ACR_LOGIN_SERVER/roster-bridge-jpp:latest \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USERNAME \
  --registry-password $ACR_PASSWORD \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 5 \
  --cpu 1.0 \
  --memory 2.0Gi
```

## 環境変数の設定

### Azure App Service の場合

```bash
# アプリケーション設定の追加
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings \
    DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require" \
    DEBUG=False \
    LOG_LEVEL=INFO \
    API_KEY=your-production-api-key \
    USE_EXTERNAL_API_KEYS=True \
    MAX_FILE_SIZE_MB=100 \
    UPLOAD_DIRECTORY=/tmp/uploads
```

### Azure Container Apps の場合

```bash
# 環境変数の更新
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --set-env-vars \
    DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require" \
    DEBUG=False \
    LOG_LEVEL=INFO \
    API_KEY=your-production-api-key \
    USE_EXTERNAL_API_KEYS=True \
    MAX_FILE_SIZE_MB=100 \
    UPLOAD_DIRECTORY=/tmp/uploads
```

## SSL/TLS の設定

### カスタムドメインの設定（App Service）

```bash
# カスタムドメインの追加
az webapp config hostname add \
  --webapp-name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --hostname your-domain.com

# SSL 証明書の取得（Let's Encrypt）
az webapp config ssl bind \
  --certificate-source AppService \
  --hostname your-domain.com \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## 監視とログ

### Application Insights の設定

```bash
# Application Insights の作成
az monitor app-insights component create \
  --app "${APP_NAME}-insights" \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP

# インストルメンテーションキーの取得
export APPINSIGHTS_KEY=$(az monitor app-insights component show \
  --app "${APP_NAME}-insights" \
  --resource-group $RESOURCE_GROUP \
  --query "instrumentationKey" --output tsv)

# アプリケーション設定に追加
az webapp config appsettings set \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=$APPINSIGHTS_KEY
```

### ログストリーミング

```bash
# App Service のログストリーミング
az webapp log tail --name $APP_NAME --resource-group $RESOURCE_GROUP

# Container Apps のログ表示
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

## スケーリング

### Auto Scaling の設定（App Service）

```bash
# スケールアウトルールの作成
az monitor autoscale create \
  --resource-group $RESOURCE_GROUP \
  --resource $APP_NAME \
  --resource-type Microsoft.Web/serverfarms \
  --name "${APP_NAME}-autoscale" \
  --min-count 1 \
  --max-count 5 \
  --count 2

# CPU ベースのスケールルール
az monitor autoscale rule create \
  --resource-group $RESOURCE_GROUP \
  --autoscale-name "${APP_NAME}-autoscale" \
  --condition "Percentage CPU > 70 avg 5m" \
  --scale out 1
```

### Container Apps のスケーリング

```bash
# スケーリングルールの更新
az containerapp update \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --min-replicas 1 \
  --max-replicas 10 \
  --scale-rule-name http-rule \
  --scale-rule-type http \
  --scale-rule-metadata concurrentRequests=100
```

## セキュリティ設定

### Key Vault の使用

```bash
# Key Vault の作成
az keyvault create \
  --name "${APP_NAME}-kv" \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# シークレットの保存
az keyvault secret set \
  --vault-name "${APP_NAME}-kv" \
  --name "database-url" \
  --value "postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"

# Managed Identity の有効化
az webapp identity assign \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP

# Key Vault アクセス許可の設定
export PRINCIPAL_ID=$(az webapp identity show --name $APP_NAME --resource-group $RESOURCE_GROUP --query principalId --output tsv)

az keyvault set-policy \
  --name "${APP_NAME}-kv" \
  --object-id $PRINCIPAL_ID \
  --secret-permissions get
```

## バックアップ戦略

### データベースバックアップ

```bash
# 自動バックアップの確認
az postgres flexible-server show \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --query "backup"

# ポイントインタイムリストア（例）
az postgres flexible-server restore \
  --resource-group $RESOURCE_GROUP \
  --name "${DB_SERVER_NAME}-restored" \
  --source-server $DB_SERVER_NAME \
  --restore-time "2025-05-25T10:00:00Z"
```

### アプリケーションバックアップ

```bash
# App Service バックアップの設定
az webapp config backup create \
  --resource-group $RESOURCE_GROUP \
  --webapp-name $APP_NAME \
  --backup-name "daily-backup" \
  --storage-account-url "https://yourstorageaccount.blob.core.windows.net/backups" \
  --frequency 1440 \
  --retain-one true
```

## 継続的デプロイメント

### GitHub Actions の設定

`.github/workflows/azure-deploy.yml` ファイルを作成：

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v2
    
    - name: Log in to Azure Container Registry
      uses: azure/docker-login@v1
      with:
        login-server: ${{ secrets.REGISTRY_LOGIN_SERVER }}
        username: ${{ secrets.REGISTRY_USERNAME }}
        password: ${{ secrets.REGISTRY_PASSWORD }}
    
    - name: Build and push image
      uses: docker/build-push-action@v3
      with:
        context: .
        push: true
        tags: ${{ secrets.REGISTRY_LOGIN_SERVER }}/roster-bridge-jpp:${{ github.sha }}
    
    - name: Deploy to Azure Container Apps
      uses: azure/container-apps-deploy-action@v1
      with:
        appSourcePath: .
        acrName: ${{ secrets.REGISTRY_NAME }}
        containerAppName: ${{ secrets.CONTAINER_APP_NAME }}
        resourceGroup: ${{ secrets.RESOURCE_GROUP }}
        imageToDeploy: ${{ secrets.REGISTRY_LOGIN_SERVER }}/roster-bridge-jpp:${{ github.sha }}
```

## 性能最適化

### データベース最適化

```bash
# データベース接続プールの設定
az postgres flexible-server parameter set \
  --resource-group $RESOURCE_GROUP \
  --server-name $DB_SERVER_NAME \
  --name max_connections \
  --value 100

# 読み取りレプリカの作成（高負荷時）
az postgres flexible-server replica create \
  --replica-name "${DB_SERVER_NAME}-replica" \
  --resource-group $RESOURCE_GROUP \
  --source-server $DB_SERVER_NAME
```

### CDN の設定

```bash
# CDN プロファイルの作成
az cdn profile create \
  --resource-group $RESOURCE_GROUP \
  --name "${APP_NAME}-cdn" \
  --sku Standard_Microsoft

# CDN エンドポイントの作成
az cdn endpoint create \
  --resource-group $RESOURCE_GROUP \
  --profile-name "${APP_NAME}-cdn" \
  --name "${APP_NAME}-endpoint" \
  --origin "${APP_NAME}.azurewebsites.net"
```

## 運用・メンテナンス

### 日常運用

#### システム状態の確認

```bash
# 総合状態確認
./scripts/maintenance.sh status

# 詳細なヘルスチェック
./scripts/maintenance.sh health

# リソース使用状況確認
az monitor metrics list \
  --resource $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --resource-type Microsoft.App/containerApps \
  --metric "Requests,CpuUsage,MemoryUsage"
```

#### ログ管理

```bash
# ログ収集と分析
./scripts/maintenance.sh logs

# リアルタイムログ監視
az containerapp logs tail \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --follow

# Application Insights クエリ
az monitor app-insights query \
  --app "${APP_NAME}-insights" \
  --analytics-query "requests | where timestamp > ago(1h) | summarize count() by resultCode"
```

#### メンテナンス作業

```bash
# 定期メンテナンス（推奨: 月1回）
./scripts/maintenance.sh cleanup

# アプリケーション更新
./scripts/maintenance.sh update

# スケーリング調整
./scripts/maintenance.sh scale

# システム再起動（必要時のみ）
./scripts/maintenance.sh restart
```

### バックアップ・復旧

#### 定期バックアップ

```bash
# バックアップ実行
./scripts/maintenance.sh backup

# データベースの手動バックアップ
az postgres flexible-server backup create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --backup-name "manual-backup-$(date +%Y%m%d)"
```

#### 復旧手順

```bash
# ポイントインタイム復旧
az postgres flexible-server restore \
  --resource-group $RESOURCE_GROUP \
  --name "${DB_SERVER_NAME}-restored" \
  --source-server $DB_SERVER_NAME \
  --restore-time "2025-01-25T10:00:00Z"

# アプリケーション復旧
az containerapp revision activate \
  --resource-group $RESOURCE_GROUP \
  --app $APP_NAME \
  --name "previous-stable-revision"
```

### 運用監視

#### アラート設定

```bash
# 監視アラート設定
./scripts/setup-monitoring.sh

# カスタムアラート作成
az monitor metrics alert create \
  --name "High-CPU-Alert" \
  --resource-group $RESOURCE_GROUP \
  --scopes "/subscriptions/{subscription-id}/resourceGroups/$RESOURCE_GROUP/providers/Microsoft.App/containerApps/$APP_NAME" \
  --condition "avg cpu_usage > 80" \
  --description "CPU使用率が80%を超えました"
```

#### パフォーマンス分析

```bash
# Application Insights での分析
az monitor app-insights query \
  --app "${APP_NAME}-insights" \
  --analytics-query "
    requests 
    | where timestamp > ago(24h) 
    | summarize 
        avgDuration=avg(duration),
        p95Duration=percentile(duration, 95),
        requestCount=count()
    by bin(timestamp, 1h)
    | order by timestamp desc
  "
```

## コスト最適化

### コスト分析

```bash
# 詳細なコスト分析
./scripts/cost-optimization.sh $RESOURCE_GROUP $ENVIRONMENT

# 月次コストレポート
az consumption usage list \
  --start-date "$(date -d '30 days ago' +%Y-%m-%d)" \
  --end-date "$(date +%Y-%m-%d)" \
  --query "[?contains(instanceName, '$RESOURCE_GROUP')]" \
  --output table
```

### 自動最適化

```bash
# リソース使用率チェック
az monitor metrics list \
  --resource $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --resource-type Microsoft.App/containerApps \
  --metric "CpuUsage,MemoryUsage" \
  --start-time "$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%SZ)" \
  --aggregation Average

# 未使用リソースの検出
az resource list \
  --resource-group $RESOURCE_GROUP \
  --query "[?tags.Environment=='$ENVIRONMENT' && tags.LastUsed < '$(date -d '30 days ago' +%Y-%m-%d)']"
```

### 予算管理

```bash
# 予算アラート設定
az consumption budget create \
  --resource-group $RESOURCE_GROUP \
  --budget-name "monthly-budget" \
  --amount 50000 \
  --time-grain Monthly \
  --start-date "$(date +%Y-%m-01)" \
  --end-date "$(date -d '+12 months' +%Y-%m-01)"
```

### 運用自動化

#### 定期実行スケジュール

運用作業の自動化には、以下のスケジュールを推奨します：

```bash
# Crontab例（Linux/macOS）
# 毎日午前2時にヘルスチェック
0 2 * * * /path/to/scripts/maintenance.sh health >> /var/log/azure-health.log 2>&1

# 毎週日曜日午前3時にバックアップ
0 3 * * 0 /path/to/scripts/maintenance.sh backup >> /var/log/azure-backup.log 2>&1

# 毎月1日午前4時にクリーンアップ
0 4 1 * * /path/to/scripts/maintenance.sh cleanup >> /var/log/azure-cleanup.log 2>&1

# 毎月第1月曜日にコスト分析
0 5 * * 1 [ $(date +\%d) -le 7 ] && /path/to/scripts/cost-optimization.sh >> /var/log/azure-cost.log 2>&1
```

#### 自動復旧

```bash
# ヘルスチェック失敗時の自動復旧スクリプト例
#!/bin/bash
if ! curl -f "https://$APP_URL/health" > /dev/null 2>&1; then
    echo "Health check failed, attempting restart..."
    ./scripts/maintenance.sh restart
    sleep 60
    if curl -f "https://$APP_URL/health" > /dev/null 2>&1; then
        echo "Application recovered successfully"
    else
        echo "ALERT: Manual intervention required"
        # Send alert to team
    fi
fi
```

## トラブルシューティング

### 一般的な問題と解決方法

#### 1. データベース接続エラー

```bash
# ファイアウォールルールの確認
az postgres flexible-server firewall-rule list \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME

# 必要に応じてファイアウォールルールを追加
az postgres flexible-server firewall-rule create \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --rule-name "AllowAzureServices" \
  --start-ip-address 0.0.0.0 \
  --end-ip-address 0.0.0.0
```

#### 2. アプリケーションが起動しない

```bash
# ログの確認
az webapp log download \
  --resource-group $RESOURCE_GROUP \
  --name $APP_NAME

# または Container Apps の場合
az containerapp logs show \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP
```

#### 3. 高負荷時のパフォーマンス問題

```bash
# CPU/メモリ使用率の確認
az monitor metrics list \
  --resource $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --resource-type Microsoft.Web/sites \
  --metric "CpuPercentage,MemoryPercentage"
```

### 診断コマンド

```bash
# リソースの状態確認
az resource list --resource-group $RESOURCE_GROUP --output table

# ネットワーク接続の確認
az network vnet show --resource-group $RESOURCE_GROUP --name vnet-roster-bridge

# セキュリティ設定の確認
az security assessment list --resource-group $RESOURCE_GROUP
```

## 費用最適化

### リソースのサイズ調整

```bash
# App Service Plan のスケールダウン
az appservice plan update \
  --name "${APP_NAME}-plan" \
  --resource-group $RESOURCE_GROUP \
  --sku B1

# データベースのサイズ調整
az postgres flexible-server update \
  --resource-group $RESOURCE_GROUP \
  --name $DB_SERVER_NAME \
  --sku-name Standard_B1ms
```

### 費用分析

```bash
# 費用分析の表示
az consumption usage list \
  --start-date 2025-05-01 \
  --end-date 2025-05-31 \
  --query "[?contains(instanceName, 'roster-bridge')]"
```

## まとめ

このガイドに従って、Roster Bridge JPP アプリケーションを Azure に正常にデプロイできます。本番環境では以下の点に注意してください：

1. **セキュリティ**: 強力なパスワード、Key Vault の使用、ネットワークセキュリティの設定
2. **可用性**: 複数のリージョンへのデプロイ、バックアップ戦略の実装
3. **監視**: Application Insights、アラートの設定
4. **費用管理**: リソースサイズの最適化、不要なリソースの削除

詳細な質問やトラブルシューティングが必要な場合は、Azure サポートにお問い合わせください。
