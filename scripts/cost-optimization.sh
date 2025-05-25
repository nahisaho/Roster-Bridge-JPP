#!/bin/bash

# Azure コスト最適化スクリプト
# 使用方法: ./cost-optimization.sh [resource-group] [environment]

set -e

# デフォルト値
RESOURCE_GROUP=${1:-rg-roster-bridge-prod}
ENVIRONMENT=${2:-prod}

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

# コスト分析
analyze_costs() {
    log_info "コスト分析を実行しています..."
    
    # 過去30日のコスト取得
    local end_date=$(date -d "today" +%Y-%m-%d)
    local start_date=$(date -d "30 days ago" +%Y-%m-%d)
    
    echo "分析期間: $start_date ～ $end_date"
    echo ""
    
    # リソースグループのコスト取得
    log_info "リソースグループ '$RESOURCE_GROUP' のコスト分析..."
    
    az consumption usage list \
        --start-date $start_date \
        --end-date $end_date \
        --query "[?contains(instanceName, '$RESOURCE_GROUP')]" \
        --output table
    
    echo ""
}

# 未使用リソースの検出
detect_unused_resources() {
    log_info "未使用リソースを検出しています..."
    
    # 停止中のVM
    local stopped_vms=$(az vm list \
        --resource-group $RESOURCE_GROUP \
        --query "[?powerState!='VM running'].{Name:name, PowerState:powerState}" \
        --output table)
    
    if [ -n "$stopped_vms" ]; then
        log_warning "停止中のVMが見つかりました:"
        echo "$stopped_vms"
        echo ""
    fi
    
    # 未使用のディスク
    local unattached_disks=$(az disk list \
        --resource-group $RESOURCE_GROUP \
        --query "[?managedBy==null].{Name:name, Size:diskSizeGb, Tier:sku.tier}" \
        --output table)
    
    if [ -n "$unattached_disks" ]; then
        log_warning "未接続のディスクが見つかりました:"
        echo "$unattached_disks"
        echo ""
    fi
    
    # 未使用のNIC
    local unused_nics=$(az network nic list \
        --resource-group $RESOURCE_GROUP \
        --query "[?virtualMachine==null].{Name:name, Location:location}" \
        --output table)
    
    if [ -n "$unused_nics" ]; then
        log_warning "未使用のネットワークインターフェースが見つかりました:"
        echo "$unused_nics"
        echo ""
    fi
}

# リソースサイズの最適化提案
suggest_optimizations() {
    log_info "最適化提案を生成しています..."
    
    # App Service のメトリクス確認
    local app_services=$(az webapp list \
        --resource-group $RESOURCE_GROUP \
        --query "[].name" \
        --output tsv)
    
    for app in $app_services; do
        log_info "App Service: $app の使用率を確認中..."
        
        # CPU使用率チェック
        local cpu_avg=$(az monitor metrics list \
            --resource $app \
            --resource-group $RESOURCE_GROUP \
            --resource-type Microsoft.Web/sites \
            --metric "CpuPercentage" \
            --start-time "$(date -d '7 days ago' -u +%Y-%m-%dT%H:%M:%SZ)" \
            --end-time "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --aggregation Average \
            --query "value[0].timeseries[0].data[*].average" \
            --output tsv 2>/dev/null | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
        
        if (( $(echo "$cpu_avg < 20" | bc -l) )); then
            log_warning "  → CPU使用率が低い ($cpu_avg%) - より小さいプランを検討してください"
        elif (( $(echo "$cpu_avg > 80" | bc -l) )); then
            log_warning "  → CPU使用率が高い ($cpu_avg%) - より大きいプランを検討してください"
        fi
    done
    
    # PostgreSQL の使用率確認
    local db_servers=$(az postgres flexible-server list \
        --resource-group $RESOURCE_GROUP \
        --query "[].name" \
        --output tsv)
    
    for db in $db_servers; do
        log_info "PostgreSQL Server: $db の設定を確認中..."
        
        local db_sku=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "sku.name" \
            --output tsv)
        
        local storage_size=$(az postgres flexible-server show \
            --resource-group $RESOURCE_GROUP \
            --name $db \
            --query "storage.storageSizeGB" \
            --output tsv)
        
        echo "  現在の設定: SKU=$db_sku, ストレージ=${storage_size}GB"
        
        if [[ "$db_sku" == *"Standard_D"* ]]; then
            log_warning "  → より安価なBurstableプランの検討を推奨します"
        fi
    done
}

# 自動最適化の実行
apply_optimizations() {
    log_warning "自動最適化を実行しますか？ (y/N)"
    read -r response
    
    if [[ ! "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        log_info "最適化をスキップしました"
        return
    fi
    
    log_info "自動最適化を実行しています..."
    
    # App Service プランのダウンサイジング（低使用率の場合）
    local app_plans=$(az appservice plan list \
        --resource-group $RESOURCE_GROUP \
        --query "[].name" \
        --output tsv)
    
    for plan in $app_plans; do
        local current_sku=$(az appservice plan show \
            --resource-group $RESOURCE_GROUP \
            --name $plan \
            --query "sku.name" \
            --output tsv)
        
        if [[ "$current_sku" == "S1" || "$current_sku" == "S2" ]]; then
            log_info "App Service Plan '$plan' を B1 にダウンサイジング中..."
            
            az appservice plan update \
                --resource-group $RESOURCE_GROUP \
                --name $plan \
                --sku B1 \
                --output table
            
            log_success "App Service Plan をダウンサイジングしました"
        fi
    done
    
    # 未使用ディスクの削除確認
    local unattached_disks=$(az disk list \
        --resource-group $RESOURCE_GROUP \
        --query "[?managedBy==null].name" \
        --output tsv)
    
    for disk in $unattached_disks; do
        log_warning "未使用ディスク '$disk' を削除しますか？ (y/N)"
        read -r disk_response
        
        if [[ "$disk_response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            az disk delete \
                --resource-group $RESOURCE_GROUP \
                --name $disk \
                --yes \
                --output table
            
            log_success "ディスク '$disk' を削除しました"
        fi
    done
}

# 予算アラートの設定
setup_budget_alerts() {
    log_info "予算アラートを設定しています..."
    
    # サブスクリプションID取得
    local subscription_id=$(az account show --query "id" --output tsv)
    
    # 月額予算の設定（例: 50,000円）
    local budget_amount=50000
    local budget_name="roster-bridge-monthly-budget"
    
    # 予算作成（Azure CLIの予算コマンドは制限されているため、ARM テンプレートを使用）
    cat > budget-template.json << EOF
{
    "\$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {
        "budgetName": {
            "type": "string",
            "defaultValue": "$budget_name"
        },
        "amount": {
            "type": "int",
            "defaultValue": $budget_amount
        }
    },
    "resources": [
        {
            "type": "Microsoft.Consumption/budgets",
            "apiVersion": "2019-10-01",
            "name": "[parameters('budgetName')]",
            "properties": {
                "timePeriod": {
                    "startDate": "$(date +%Y-%m-01)",
                    "endDate": "$(date -d '+12 months' +%Y-%m-01)"
                },
                "timeGrain": "Monthly",
                "amount": "[parameters('amount')]",
                "category": "Cost",
                "notifications": {
                    "alert1": {
                        "enabled": true,
                        "operator": "GreaterThan",
                        "threshold": 80,
                        "contactEmails": ["admin@example.com"]
                    },
                    "alert2": {
                        "enabled": true,
                        "operator": "GreaterThan",
                        "threshold": 100,
                        "contactEmails": ["admin@example.com"]
                    }
                }
            }
        }
    ]
}
EOF
    
    log_info "予算テンプレートを生成しました (budget-template.json)"
    log_info "以下のコマンドで予算を設定できます:"
    echo "az deployment sub create --location japaneast --template-file budget-template.json"
}

# コスト最適化レポートの生成
generate_cost_report() {
    log_info "コスト最適化レポートを生成しています..."
    
    local report_file="cost-optimization-report-$(date +%Y%m%d).txt"
    
    {
        echo "=== Azure コスト最適化レポート ==="
        echo "生成日時: $(date)"
        echo "リソースグループ: $RESOURCE_GROUP"
        echo "環境: $ENVIRONMENT"
        echo ""
        
        echo "=== リソース使用状況 ==="
        az resource list --resource-group $RESOURCE_GROUP --output table
        echo ""
        
        echo "=== コスト分析（過去30日） ==="
        local end_date=$(date -d "today" +%Y-%m-%d)
        local start_date=$(date -d "30 days ago" +%Y-%m-%d)
        
        az consumption usage list \
            --start-date $start_date \
            --end-date $end_date \
            --query "[?contains(instanceName, '$RESOURCE_GROUP')]" \
            --output table
        
        echo ""
        echo "=== 最適化提案 ==="
        echo "1. 低使用率リソースの確認とダウンサイジング"
        echo "2. 未使用リソースの削除"
        echo "3. 予約インスタンスの活用検討"
        echo "4. 自動シャットダウンの設定"
        echo "5. アーカイブストレージの活用"
        
    } > "$report_file"
    
    log_success "レポートを生成しました: $report_file"
}

# メイン実行
main() {
    log_info "=== Azure コスト最適化ツール ==="
    log_info "リソースグループ: $RESOURCE_GROUP"
    log_info "環境: $ENVIRONMENT"
    echo ""
    
    analyze_costs
    detect_unused_resources
    suggest_optimizations
    apply_optimizations
    setup_budget_alerts
    generate_cost_report
    
    log_success "=== コスト最適化完了 ==="
    echo ""
    log_info "定期的な見直しを推奨します:"
    echo "1. 月次でこのスクリプトを実行"
    echo "2. Azure Cost Management + Billing の確認"
    echo "3. リソース使用状況の監視"
    echo "4. 予算アラートの設定"
}

# スクリプト実行
main "$@"
