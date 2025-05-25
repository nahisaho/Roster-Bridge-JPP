#!/bin/bash

# Azure デプロイメント自動化スクリプト
# 使用方法: ./deploy-to-azure.sh [environment] [app-name]

set -e

# デフォルト値
ENVIRONMENT=${1:-prod}
APP_NAME=${2:-roster-bridge-jpp}
LOCATION=${3:-japaneast}

# 色付きの出力
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ログ関数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 前提条件チェック
check_prerequisites() {
    log_info "前提条件をチェックしています..."
    
    # Azure CLI のチェック
    if ! command -v az &> /dev/null; then
        log_error "Azure CLI がインストールされていません"
        exit 1
    fi
    
    # Docker のチェック
    if ! command -v docker &> /dev/null; then
        log_error "Docker がインストールされていません"
        exit 1
    fi
    
    # Azure ログイン確認
    if ! az account show &> /dev/null; then
        log_error "Azure にログインしていません。 'az login' を実行してください"
        exit 1
    fi
    
    log_success "前提条件チェック完了"
}

# 環境変数設定
setup_environment() {
    log_info "環境変数を設定しています..."
    
    export RESOURCE_GROUP="rg-${APP_NAME}-${ENVIRONMENT}"
    export ACR_NAME="${APP_NAME}acr${ENVIRONMENT}"
    export DB_SERVER_NAME="${APP_NAME}-db-${ENVIRONMENT}"
    export DB_NAME="roster_bridge"
    export DB_ADMIN_USER="rosteradmin"
    export KEY_VAULT_NAME="${APP_NAME}-kv-${ENVIRONMENT}"
    export CONTAINER_APP_ENV="${APP_NAME}-env-${ENVIRONMENT}"
    
    # パスワード生成
    export DB_ADMIN_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    export API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
    
    log_success "環境変数設定完了"
    log_info "リソースグループ: $RESOURCE_GROUP"
    log_info "場所: $LOCATION"
    log_info "アプリ名: $APP_NAME"
}

# リソースグループ作成
create_resource_group() {
    log_info "リソースグループを作成しています..."
    
    az group create \
        --name $RESOURCE_GROUP \
        --location $LOCATION \
        --tags \
            Environment=$ENVIRONMENT \
            Application="Roster-Bridge-JPP" \
            Owner="DevOps-Team" \
            CreatedBy="deploy-script" \
            Version="1.0" \
        --output table
    
    log_success "リソースグループ作成完了: $RESOURCE_GROUP"
}

# Key Vault 作成
create_key_vault() {
    log_info "Key Vault を作成しています..."
    
    az keyvault create \
        --name $KEY_VAULT_NAME \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --tags \
            Environment=$ENVIRONMENT \
            Application="Roster-Bridge-JPP" \
            Service="KeyVault" \
        --output table
    
    # シークレット保存
    log_info "シークレットを保存しています..."
    
    az keyvault secret set \
        --vault-name $KEY_VAULT_NAME \
        --name "db-admin-password" \
        --value $DB_ADMIN_PASSWORD \
        --output table
    
    az keyvault secret set \
        --vault-name $KEY_VAULT_NAME \
        --name "api-key" \
        --value $API_KEY \
        --output table
    
    log_success "Key Vault 作成完了: $KEY_VAULT_NAME"
}

# PostgreSQL データベース作成
create_database() {
    log_info "PostgreSQL データベースを作成しています..."
    
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
        --public-access 0.0.0.0-255.255.255.255 \
        --output table
    
    # データベース作成
    log_info "データベースを作成しています..."
    
    az postgres flexible-server db create \
        --resource-group $RESOURCE_GROUP \
        --server-name $DB_SERVER_NAME \
        --database-name $DB_NAME \
        --output table
    
    log_success "データベース作成完了: $DB_SERVER_NAME"
}

# Container Registry 作成
create_container_registry() {
    log_info "Container Registry を作成しています..."
    
    az acr create \
        --resource-group $RESOURCE_GROUP \
        --name $ACR_NAME \
        --sku Basic \
        --admin-enabled true \
        --output table
    
    log_success "Container Registry 作成完了: $ACR_NAME"
}

# Docker イメージビルドとプッシュ
build_and_push_image() {
    log_info "Docker イメージをビルドしています..."
    
    # ACR にログイン
    az acr login --name $ACR_NAME
    
    # ログインサーバー取得
    export ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query "loginServer" --output tsv)
    
    # イメージビルド
    docker build -t $ACR_LOGIN_SERVER/$APP_NAME:latest .
    
    # イメージプッシュ
    log_info "Docker イメージをプッシュしています..."
    docker push $ACR_LOGIN_SERVER/$APP_NAME:latest
    
    log_success "Docker イメージのビルドとプッシュ完了"
}

# Container Apps 環境作成
create_container_apps_environment() {
    log_info "Container Apps 環境を作成しています..."
    
    az containerapp env create \
        --name $CONTAINER_APP_ENV \
        --resource-group $RESOURCE_GROUP \
        --location $LOCATION \
        --output table
    
    log_success "Container Apps 環境作成完了: $CONTAINER_APP_ENV"
}

# アプリケーションデプロイ
deploy_application() {
    log_info "アプリケーションをデプロイしています..."
    
    # ACR 認証情報取得
    export ACR_USERNAME=$(az acr credential show --name $ACR_NAME --query "username" --output tsv)
    export ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" --output tsv)
    
    # データベース接続文字列作成
    export DATABASE_URL="postgresql://${DB_ADMIN_USER}:${DB_ADMIN_PASSWORD}@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"
    
    # Container App 作成
    az containerapp create \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --environment $CONTAINER_APP_ENV \
        --image $ACR_LOGIN_SERVER/$APP_NAME:latest \
        --registry-server $ACR_LOGIN_SERVER \
        --registry-username $ACR_USERNAME \
        --registry-password $ACR_PASSWORD \
        --target-port 8000 \
        --ingress external \
        --min-replicas 1 \
        --max-replicas 5 \
        --cpu 1.0 \
        --memory 2.0Gi \
        --env-vars \
            DATABASE_URL="$DATABASE_URL" \
            DEBUG=False \
            LOG_LEVEL=INFO \
            API_KEY="$API_KEY" \
            USE_EXTERNAL_API_KEYS=True \
            MAX_FILE_SIZE_MB=100 \
            UPLOAD_DIRECTORY=/tmp/uploads \
        --output table
    
    log_success "アプリケーションデプロイ完了"
}

# Application Insights 設定
setup_monitoring() {
    log_info "Application Insights を設定しています..."
    
    az monitor app-insights component create \
        --app "${APP_NAME}-insights-${ENVIRONMENT}" \
        --location $LOCATION \
        --resource-group $RESOURCE_GROUP \
        --output table
    
    # インストルメンテーションキー取得
    export APPINSIGHTS_KEY=$(az monitor app-insights component show \
        --app "${APP_NAME}-insights-${ENVIRONMENT}" \
        --resource-group $RESOURCE_GROUP \
        --query "instrumentationKey" --output tsv)
    
    # Container App に追加
    az containerapp update \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --set-env-vars APPINSIGHTS_INSTRUMENTATIONKEY=$APPINSIGHTS_KEY \
        --output table
    
    log_success "Application Insights 設定完了"
}

# デプロイ結果表示
show_deployment_info() {
    log_info "デプロイメント情報を取得しています..."
    
    # アプリケーション URL 取得
    export APP_URL=$(az containerapp show \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --query "properties.configuration.ingress.fqdn" --output tsv)
    
    echo ""
    log_success "=== デプロイメント完了 ==="
    echo ""
    echo "アプリケーション URL: https://$APP_URL"
    echo "API ベース URL: https://$APP_URL/api/v1"
    echo "ヘルスチェック URL: https://$APP_URL/health"
    echo ""
    echo "リソース情報:"
    echo "  リソースグループ: $RESOURCE_GROUP"
    echo "  Container Registry: $ACR_NAME"
    echo "  データベース: $DB_SERVER_NAME"
    echo "  Key Vault: $KEY_VAULT_NAME"
    echo ""
    echo "認証情報:"
    echo "  API キー: $API_KEY"
    echo "  データベース URL: postgresql://${DB_ADMIN_USER}:[PASSWORD]@${DB_SERVER_NAME}.postgres.database.azure.com:5432/${DB_NAME}?sslmode=require"
    echo ""
    log_warning "重要: API キーとデータベースパスワードは Key Vault に保存されています"
    echo ""
}

# ヘルスチェック
health_check() {
    log_info "アプリケーションのヘルスチェックを実行しています..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "https://$APP_URL/health" > /dev/null; then
            log_success "アプリケーションが正常に起動しました"
            return 0
        fi
        
        log_info "ヘルスチェック ($attempt/$max_attempts) - 30秒後に再試行..."
        sleep 30
        ((attempt++))
    done
    
    log_error "アプリケーションのヘルスチェックに失敗しました"
    return 1
}

# クリーンアップ関数（エラー時）
cleanup_on_error() {
    log_error "エラーが発生しました。クリーンアップを実行しますか? (y/N)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_warning "リソースを削除しています..."
        az group delete --name $RESOURCE_GROUP --yes --no-wait
        log_success "クリーンアップ完了"
    fi
}

# メイン実行
main() {
    log_info "=== Azure デプロイメント開始 ==="
    log_info "環境: $ENVIRONMENT"
    log_info "アプリ名: $APP_NAME"
    log_info "場所: $LOCATION"
    echo ""
    
    # エラー時のクリーンアップ設定
    trap cleanup_on_error ERR
    
    check_prerequisites
    setup_environment
    create_resource_group
    create_key_vault
    create_database
    create_container_registry
    build_and_push_image
    create_container_apps_environment
    deploy_application
    setup_monitoring
    show_deployment_info
    health_check
    
    log_success "=== Azure デプロイメント完了 ==="
}

# スクリプト実行
main "$@"
