#!/bin/bash

# Azure 監視アラート設定スクリプト
# 使用方法: ./setup-monitoring.sh [resource-group] [app-name]

set -e

RESOURCE_GROUP=${1:-rg-roster-bridge-jpp-prod}
APP_NAME=${2:-roster-bridge-jpp}

# 色付きの出力
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_info "Azure 監視アラートを設定しています..."
log_info "リソースグループ: $RESOURCE_GROUP"
log_info "アプリ名: $APP_NAME"

# リソース ID を取得
CONTAINER_APP_ID=$(az containerapp show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "id" --output tsv)

DB_SERVER_NAME="${APP_NAME}-db"
DB_SERVER_ID=$(az postgres flexible-server show \
    --name $DB_SERVER_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "id" --output tsv 2>/dev/null || echo "")

# Action Group の作成（通知先設定）
log_info "Action Group を作成しています..."
az monitor action-group create \
    --resource-group $RESOURCE_GROUP \
    --name "${APP_NAME}-alerts" \
    --short-name "RosterAlert" \
    --action email admin admin@example.com

ACTION_GROUP_ID=$(az monitor action-group show \
    --resource-group $RESOURCE_GROUP \
    --name "${APP_NAME}-alerts" \
    --query "id" --output tsv)

# Container App のアラート設定

# 1. HTTP 5xx エラー率アラート
log_info "HTTP 5xx エラー率アラートを作成しています..."
az monitor metrics alert create \
    --name "${APP_NAME}-http-5xx-errors" \
    --resource-group $RESOURCE_GROUP \
    --scopes $CONTAINER_APP_ID \
    --condition "avg Requests where ResultCode startswith '5' > 10" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 2 \
    --description "HTTP 5xx エラー率が 10% を超えています" \
    --action $ACTION_GROUP_ID

# 2. レスポンス時間アラート
log_info "レスポンス時間アラートを作成しています..."
az monitor metrics alert create \
    --name "${APP_NAME}-response-time" \
    --resource-group $RESOURCE_GROUP \
    --scopes $CONTAINER_APP_ID \
    --condition "avg RequestDuration > 5000" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 3 \
    --description "平均レスポンス時間が 5 秒を超えています" \
    --action $ACTION_GROUP_ID

# 3. CPU 使用率アラート
log_info "CPU 使用率アラートを作成しています..."
az monitor metrics alert create \
    --name "${APP_NAME}-cpu-usage" \
    --resource-group $RESOURCE_GROUP \
    --scopes $CONTAINER_APP_ID \
    --condition "avg UsageNanoCores > 800000000" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 3 \
    --description "CPU 使用率が 80% を超えています" \
    --action $ACTION_GROUP_ID

# 4. メモリ使用率アラート
log_info "メモリ使用率アラートを作成しています..."
az monitor metrics alert create \
    --name "${APP_NAME}-memory-usage" \
    --resource-group $RESOURCE_GROUP \
    --scopes $CONTAINER_APP_ID \
    --condition "avg WorkingSetBytes > 1610612736" \
    --window-size 5m \
    --evaluation-frequency 1m \
    --severity 3 \
    --description "メモリ使用率が 80% (1.5GB) を超えています" \
    --action $ACTION_GROUP_ID

# データベースアラート設定（存在する場合）
if [ ! -z "$DB_SERVER_ID" ]; then
    log_info "データベースアラートを設定しています..."
    
    # 5. データベース接続数アラート
    az monitor metrics alert create \
        --name "${APP_NAME}-db-connections" \
        --resource-group $RESOURCE_GROUP \
        --scopes $DB_SERVER_ID \
        --condition "avg active_connections > 80" \
        --window-size 5m \
        --evaluation-frequency 1m \
        --severity 2 \
        --description "データベース接続数が 80 を超えています" \
        --action $ACTION_GROUP_ID
    
    # 6. データベース CPU 使用率アラート
    az monitor metrics alert create \
        --name "${APP_NAME}-db-cpu" \
        --resource-group $RESOURCE_GROUP \
        --scopes $DB_SERVER_ID \
        --condition "avg cpu_percent > 80" \
        --window-size 5m \
        --evaluation-frequency 1m \
        --severity 3 \
        --description "データベース CPU 使用率が 80% を超えています" \
        --action $ACTION_GROUP_ID
fi

# Application Insights アラート
APP_INSIGHTS_NAME="${APP_NAME}-insights"
APP_INSIGHTS_ID=$(az monitor app-insights component show \
    --app $APP_INSIGHTS_NAME \
    --resource-group $RESOURCE_GROUP \
    --query "id" --output tsv 2>/dev/null || echo "")

if [ ! -z "$APP_INSIGHTS_ID" ]; then
    log_info "Application Insights アラートを設定しています..."
    
    # 7. 例外レートアラート
    az monitor metrics alert create \
        --name "${APP_NAME}-exceptions" \
        --resource-group $RESOURCE_GROUP \
        --scopes $APP_INSIGHTS_ID \
        --condition "avg exceptions/count > 5" \
        --window-size 5m \
        --evaluation-frequency 1m \
        --severity 2 \
        --description "例外レートが 5/分 を超えています" \
        --action $ACTION_GROUP_ID
    
    # 8. 可用性アラート
    az monitor metrics alert create \
        --name "${APP_NAME}-availability" \
        --resource-group $RESOURCE_GROUP \
        --scopes $APP_INSIGHTS_ID \
        --condition "avg availabilityResults/availabilityPercentage < 99" \
        --window-size 5m \
        --evaluation-frequency 1m \
        --severity 1 \
        --description "可用性が 99% を下回っています" \
        --action $ACTION_GROUP_ID
fi

# カスタムログアラート
log_info "カスタムログアラートを設定しています..."

# 9. ログエラーアラート
az monitor scheduled-query create \
    --resource-group $RESOURCE_GROUP \
    --name "${APP_NAME}-log-errors" \
    --scopes $CONTAINER_APP_ID \
    --condition-query "ContainerAppConsoleLogs_CL | where Log_s contains 'ERROR' | summarize count() by bin(TimeGenerated, 5m)" \
    --condition-threshold 10 \
    --condition-operator "GreaterThan" \
    --condition-time-aggregation "Count" \
    --evaluation-frequency 5m \
    --window-size 5m \
    --severity 2 \
    --description "5分間で ERROR ログが 10 件を超えています" \
    --action-groups $ACTION_GROUP_ID

log_success "監視アラートの設定が完了しました"

# 設定されたアラートの一覧表示
log_info "設定されたアラート:"
az monitor metrics alert list \
    --resource-group $RESOURCE_GROUP \
    --query "[].{Name:name, Severity:severity, Description:description}" \
    --output table

log_info "監視設定完了！以下のメトリクスが監視されています:"
echo "✅ HTTP 5xx エラー率"
echo "✅ レスポンス時間"
echo "✅ CPU 使用率"
echo "✅ メモリ使用率"
if [ ! -z "$DB_SERVER_ID" ]; then
    echo "✅ データベース接続数"
    echo "✅ データベース CPU 使用率"
fi
if [ ! -z "$APP_INSIGHTS_ID" ]; then
    echo "✅ 例外レート"
    echo "✅ 可用性"
fi
echo "✅ ログエラー"
