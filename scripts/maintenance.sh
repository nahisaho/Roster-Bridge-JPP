#!/bin/bash

# Azure メンテナンススクリプト
# 使用方法: ./maintenance.sh [action] [resource-group] [environment]

set -e

# パラメータ
ACTION=${1:-status}
RESOURCE_GROUP=${2:-rg-roster-bridge-prod}
ENVIRONMENT=${3:-prod}

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

# ヘルプ表示
show_help() {
    cat << EOF
Azure メンテナンススクリプト

使用方法:
  $0 [action] [resource-group] [environment]

アクション:
  status      - システム状態の確認（デフォルト）
  health      - ヘルスチェックの実行
  logs        - ログの収集と分析
  backup      - バックアップの実行
  update      - システムアップデート
  scale       - スケーリング操作
  restart     - アプリケーションの再起動
  cleanup     - クリーンアップ作業
  report      - 総合レポート生成

例:
  $0 status
  $0 health rg-roster-bridge-prod prod
  $0 backup rg-roster-bridge-staging staging

EOF
}

# システム状態確認
check_status() {
    log_info "システム状態を確認しています..."
    
    echo "=== リソースグループ情報 ==="
    az group show --name $RESOURCE_GROUP --output table
    echo ""
    
    echo "=== アプリケーション状態 ==="
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        local app_status=$(az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "properties.latestRevisionName" \
            --output tsv)
        
        local replicas=$(az containerapp revision show \
            --name $app_status \
            --resource-group $RESOURCE_GROUP \
            --query "properties.replicas" \
            --output tsv 2>/dev/null || echo "0")
        
        echo "Container App: $app"
        echo "  リビジョン: $app_status"
        echo "  レプリカ数: $replicas"
        echo ""
    done
    
    echo "=== データベース状態 ==="
    local db_servers=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for db in $db_servers; do
        local db_state=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "state" \
            --output tsv)
        
        echo "PostgreSQL Server: $db"
        echo "  状態: $db_state"
        
        # 接続テスト
        local fqdn=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "fullyQualifiedDomainName" \
            --output tsv)
        
        if timeout 5 bash -c "cat < /dev/null > /dev/tcp/${fqdn}/5432" 2>/dev/null; then
            echo "  接続: ✅ 正常"
        else
            echo "  接続: ❌ 失敗"
        fi
        echo ""
    done
}

# ヘルスチェック実行
run_health_check() {
    log_info "ヘルスチェックを実行しています..."
    
    # Container Apps のヘルスチェック
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        local app_url=$(az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "properties.configuration.ingress.fqdn" \
            --output tsv)
        
        if [ -n "$app_url" ]; then
            echo "Container App: $app"
            echo "  URL: https://$app_url"
            
            # ヘルスエンドポイントをテスト
            if curl -f -s "https://$app_url/health" > /dev/null; then
                echo "  ヘルス: ✅ 正常"
            else
                echo "  ヘルス: ❌ 異常"
            fi
            
            # レスポンス時間測定
            local response_time=$(curl -o /dev/null -s -w "%{time_total}" "https://$app_url/health" || echo "timeout")
            echo "  レスポンス時間: ${response_time}秒"
            echo ""
        fi
    done
    
    # データベース接続確認
    local db_servers=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for db in $db_servers; do
        echo "PostgreSQL Server: $db"
        
        # データベースメトリクス確認
        local cpu_usage=$(az monitor metrics list \
            --resource $db \
            --resource-group $RESOURCE_GROUP \
            --resource-type Microsoft.DBforPostgreSQL/flexibleServers \
            --metric "cpu_percent" \
            --start-time "$(date -d '1 hour ago' -u +%Y-%m-%dT%H:%M:%SZ)" \
            --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --aggregation Average \
            --query "value[0].timeseries[0].data[-1].average" \
            --output tsv 2>/dev/null || echo "N/A")
        
        echo "  CPU使用率: ${cpu_usage}%"
        echo ""
    done
}

# ログ収集と分析
collect_logs() {
    log_info "ログを収集しています..."
    
    local log_dir="logs-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$log_dir"
    
    # Container Apps のログ
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        log_info "Container App '$app' のログを収集中..."
        
        az containerapp logs show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --follow false \
            > "$log_dir/${app}-logs.txt" 2>&1 || true
    done
    
    # Application Insights のログ（過去24時間）
    local app_insights=$(az monitor app-insights component list \
        --resource-group $RESOURCE_GROUP \
        --query "[].name" \
        --output tsv)
    
    for insights in $app_insights; do
        log_info "Application Insights '$insights' のデータを収集中..."
        
        # 例外ログ
        az monitor app-insights query \
            --app $insights \
            --analytics-query "exceptions | where timestamp > ago(24h) | order by timestamp desc" \
            --output table > "$log_dir/${insights}-exceptions.txt" 2>&1 || true
        
        # リクエストログ
        az monitor app-insights query \
            --app $insights \
            --analytics-query "requests | where timestamp > ago(24h) | summarize count() by resultCode | order by count_ desc" \
            --output table > "$log_dir/${insights}-requests.txt" 2>&1 || true
    done
    
    # ログ分析レポート生成
    {
        echo "=== ログ分析レポート ==="
        echo "生成日時: $(date)"
        echo "期間: 過去24時間"
        echo ""
        
        echo "=== エラー分析 ==="
        if ls "$log_dir"/*-logs.txt >/dev/null 2>&1; then
            grep -i "error\|exception\|fail" "$log_dir"/*-logs.txt | head -20 || echo "エラーは見つかりませんでした"
        fi
        echo ""
        
        echo "=== 警告分析 ==="
        if ls "$log_dir"/*-logs.txt >/dev/null 2>&1; then
            grep -i "warning\|warn" "$log_dir"/*-logs.txt | head -10 || echo "警告は見つかりませんでした"
        fi
        
    } > "$log_dir/analysis-report.txt"
    
    log_success "ログ収集完了: $log_dir/"
}

# バックアップ実行
run_backup() {
    log_info "バックアップを実行しています..."
    
    # データベースバックアップ
    local db_servers=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for db in $db_servers; do
        log_info "PostgreSQL Server '$db' のバックアップを確認中..."
        
        # 最新のバックアップポイント確認
        local earliest_restore=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "backup.earliestRestoreDate" \
            --output tsv)
        
        echo "  最古復元可能時点: $earliest_restore"
        
        # バックアップ設定確認
        local backup_retention=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "backup.backupRetentionDays" \
            --output tsv)
        
        echo "  バックアップ保持期間: ${backup_retention}日"
        echo ""
    done
    
    # 設定ファイルのバックアップ
    local backup_dir="config-backup-$(date +%Y%m%d)"
    mkdir -p "$backup_dir"
    
    # Container Apps 設定のエクスポート
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            > "$backup_dir/${app}-config.json"
    done
    
    log_success "設定ファイルバックアップ完了: $backup_dir/"
}

# システムアップデート
run_update() {
    log_info "システムアップデートを実行しています..."
    
    log_warning "本番環境でのアップデートは慎重に行ってください。"
    log_warning "続行しますか？ (y/N)"
    read -r response
    
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "アップデートをキャンセルしました"
        return
    fi
    
    # Container Apps の新しいリビジョンデプロイ
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        log_info "Container App '$app' を更新中..."
        
        # 現在のイメージ確認
        local current_image=$(az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "properties.template.containers[0].image" \
            --output tsv)
        
        echo "  現在のイメージ: $current_image"
        
        # 最新イメージへの更新（:latest タグを使用）
        if [[ "$current_image" == *":latest" ]]; then
            az containerapp update \
                --name $app \
                --resource-group $RESOURCE_GROUP \
                --image $current_image \
                --output table
            
            log_success "Container App '$app' を更新しました"
        else
            log_warning "Container App '$app' は固定タグを使用しています"
        fi
    done
}

# スケーリング操作
manage_scaling() {
    log_info "スケーリング設定を確認しています..."
    
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        echo "Container App: $app"
        
        # 現在のスケール設定
        local min_replicas=$(az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "properties.template.scale.minReplicas" \
            --output tsv)
        
        local max_replicas=$(az containerapp show \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "properties.template.scale.maxReplicas" \
            --output tsv)
        
        echo "  最小レプリカ: $min_replicas"
        echo "  最大レプリカ: $max_replicas"
        
        # 現在のレプリカ数
        local current_replicas=$(az containerapp revision list \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "[0].properties.replicas" \
            --output tsv)
        
        echo "  現在のレプリカ: $current_replicas"
        echo ""
    done
    
    log_info "スケーリングを変更しますか？ (y/N)"
    read -r response
    
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo "アプリケーション名を入力してください:"
        read -r app_name
        
        echo "最小レプリカ数を入力してください:"
        read -r min_rep
        
        echo "最大レプリカ数を入力してください:"
        read -r max_rep
        
        az containerapp update \
            --name $app_name \
            --resource-group $RESOURCE_GROUP \
            --min-replicas $min_rep \
            --max-replicas $max_rep \
            --output table
        
        log_success "スケーリング設定を更新しました"
    fi
}

# アプリケーション再起動
restart_application() {
    log_info "アプリケーションを再起動しています..."
    
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        log_warning "Container App '$app' を再起動しますか？ (y/N)"
        read -r response
        
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            # 新しいリビジョンの作成（実質的な再起動）
            az containerapp revision restart \
                --resource-group $RESOURCE_GROUP \
                --app $app \
                --output table
            
            log_success "Container App '$app' を再起動しました"
        fi
    done
}

# クリーンアップ作業
run_cleanup() {
    log_info "クリーンアップ作業を実行しています..."
    
    # 古いリビジョンの削除
    local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
    
    for app in $container_apps; do
        log_info "Container App '$app' の古いリビジョンを確認中..."
        
        # 非アクティブなリビジョンを取得
        local inactive_revisions=$(az containerapp revision list \
            --name $app \
            --resource-group $RESOURCE_GROUP \
            --query "[?properties.active==\`false\`].name" \
            --output tsv)
        
        if [ -n "$inactive_revisions" ]; then
            echo "  非アクティブなリビジョン:"
            echo "$inactive_revisions"
            
            log_warning "これらのリビジョンを削除しますか？ (y/N)"
            read -r response
            
            if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
                for revision in $inactive_revisions; do
                    az containerapp revision deactivate \
                        --resource-group $RESOURCE_GROUP \
                        --app $app \
                        --name $revision \
                        --output table
                    
                    log_success "リビジョン '$revision' を削除しました"
                done
            fi
        else
            echo "  削除対象のリビジョンはありません"
        fi
        echo ""
    done
    
    # 一時ファイルの削除
    log_info "一時ファイルを削除しています..."
    rm -rf logs-* config-backup-* budget-template.json 2>/dev/null || true
    log_success "一時ファイルを削除しました"
}

# 総合レポート生成
generate_report() {
    log_info "総合レポートを生成しています..."
    
    local report_file="maintenance-report-$(date +%Y%m%d-%H%M%S).txt"
    
    {
        echo "=== Azure メンテナンスレポート ==="
        echo "生成日時: $(date)"
        echo "リソースグループ: $RESOURCE_GROUP"
        echo "環境: $ENVIRONMENT"
        echo ""
        
        echo "=== システム概要 ==="
        az group show --name $RESOURCE_GROUP --output table
        echo ""
        
        echo "=== リソース一覧 ==="
        az resource list --resource-group $RESOURCE_GROUP --output table
        echo ""
        
        echo "=== Container Apps 状態 ==="
        local container_apps=$(az containerapp list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
        for app in $container_apps; do
            echo "アプリケーション: $app"
            az containerapp show --name $app --resource-group $RESOURCE_GROUP --query "{状態:properties.latestRevisionName,URL:properties.configuration.ingress.fqdn}" --output table
            echo ""
        done
        
        echo "=== データベース状態 ==="
        local db_servers=$(az postgres flexible-server list --resource-group $RESOURCE_GROUP --query "[].name" --output tsv)
        for db in $db_servers; do
            echo "データベース: $db"
            az postgres flexible-server show --resource-group $RESOURCE_GROUP --name $db --query "{状態:state,SKU:sku.name,ストレージ:storage.storageSizeGB}" --output table
            echo ""
        done
        
        echo "=== 推奨事項 ==="
        echo "1. 定期的なバックアップの確認"
        echo "2. セキュリティ更新の適用"
        echo "3. パフォーマンスメトリクスの監視"
        echo "4. コスト最適化の検討"
        echo "5. 障害復旧計画の見直し"
        
    } > "$report_file"
    
    log_success "レポートを生成しました: $report_file"
}

# メイン実行
main() {
    log_info "=== Azure メンテナンスツール ==="
    log_info "アクション: $ACTION"
    log_info "リソースグループ: $RESOURCE_GROUP"
    log_info "環境: $ENVIRONMENT"
    echo ""
    
    case $ACTION in
        "status")
            check_status
            ;;
        "health")
            run_health_check
            ;;
        "logs")
            collect_logs
            ;;
        "backup")
            run_backup
            ;;
        "update")
            run_update
            ;;
        "scale")
            manage_scaling
            ;;
        "restart")
            restart_application
            ;;
        "cleanup")
            run_cleanup
            ;;
        "report")
            generate_report
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "不明なアクション: $ACTION"
            show_help
            exit 1
            ;;
    esac
    
    log_success "=== メンテナンス完了 ==="
}

# スクリプト実行
main "$@"
