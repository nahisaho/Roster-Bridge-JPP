# Roster Bridge API

OneRoster Japan Profile形式のCSVファイルを処理するRoster APIサービス

## 機能

- OneRoster Japan Profile形式のCSVファイルのアップロード
- アップロードされたデータのSQL DBへの保存
- OneRoster Rest APIエンドポイントの提供（全件取得・差分取得）
- 管理者向けCRUD操作エンドポイント（データ管理・統計情報取得）
- APIキー管理機能

## 技術スタック

- Python 3.11+
- FastAPI
- SQLAlchemy (ORM)
- Docker
- PostgreSQL/MySQL/SQLite

## データベース設定

このアプリケーションは複数のデータベースをサポートしています：

### サポートされているデータベース

1. **SQLite** (開発環境推奨)
   - ファイルベースの軽量データベース
   - セットアップが簡単で開発に最適
   ```bash
   DATABASE_URL=sqlite:///./roster_bridge.db
   ```

2. **PostgreSQL** (本番環境推奨)
   - 高性能で信頼性の高いデータベース
   - 大規模なデータセットに対応
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/roster_bridge
   ```

3. **MySQL**
   - 広く使用されているデータベース
   ```bash
   DATABASE_URL=mysql+pymysql://user:password@localhost:3306/roster_bridge
   ```

4. **SQL Server**
   - Microsoft SQL Server
   ```bash
   DATABASE_URL=mssql+pyodbc://user:password@localhost:1433/roster_bridge?driver=ODBC+Driver+17+for+SQL+Server
   ```

## セットアップ

### ローカル開発環境

```bash
# Python仮想環境の作成と有効化
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
# .envファイルを編集してデータベース設定等を行う

# データベース設定例:
# 開発環境: DATABASE_URL=sqlite:///./roster_bridge.db
# 本番環境: DATABASE_URL=postgresql://user:password@localhost:5432/roster_bridge

# APIキーの設定
cp api_keys.json.example api_keys.json
# api_keys.jsonファイルを編集してAPIキーを設定

# データベースマイグレーション（テーブル作成）
alembic upgrade head

# サーバー起動
uvicorn app.main:app --reload
```

### Docker環境

```bash
# Docker イメージのビルド
docker build -t roster-bridge-api .

# SQLiteを使用してコンテナの起動
docker run -p 8000:8000 roster-bridge-api

# PostgreSQLと連携する場合（docker-compose使用）
docker-compose up -d
```

#### Docker Composeでの本番環境構築

`docker-compose.yml`を使用してPostgreSQLと連携したシステムを構築できます：

```bash
# PostgreSQL + FastAPIの起動
docker-compose up -d

# ログの確認
docker-compose logs -f

# システムの停止
docker-compose down
```

## API仕様

### 認証

すべてのAPIエンドポイントは認証キーが必要です。
`X-API-Key: <API_KEY>` ヘッダーを含めてください。

### 権限管理

APIキーには以下の権限レベルがあります：
- `read`: データ参照のみ
- `write`: データ参照・アップロード
- `admin`: 全ての操作（管理者API含む）

### エンドポイント

#### OneRoster API
- `POST /api/v1/upload` - CSVファイルのアップロード
- `GET /api/v1/{entity}` - 全件取得（entity: academicSessions, orgs, users）
- `GET /api/v1/{entity}/delta` - 差分取得

#### 管理者API（admin権限必須）
- `GET /api/v1/admin/stats` - システム統計情報取得
- `GET /api/v1/admin/users` - ユーザーリスト取得（ページネーション対応）
- `GET /api/v1/admin/users/{user_id}` - 特定ユーザー詳細取得
- `PUT /api/v1/admin/users/{user_id}` - ユーザー情報更新
- `DELETE /api/v1/admin/users/{user_id}` - ユーザー削除
- `GET /api/v1/admin/orgs` - 組織リスト取得
- `GET /api/v1/admin/academic-sessions` - 学期情報リスト取得

#### APIキー管理（admin権限必須）
- `GET /api/v1/admin/api-keys` - APIキー一覧取得
- `POST /api/v1/admin/api-keys` - 新規APIキー作成
- `DELETE /api/v1/admin/api-keys/{key_name}` - APIキー無効化
- `POST /api/v1/admin/api-keys/reload` - APIキー設定再読み込み

### 使用例

```bash
# システム統計情報を取得
curl -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "X-API-Key: dev-api-key-12345"

# ユーザーリストを取得（ページネーション）
curl -X GET "http://localhost:8000/api/v1/admin/users?limit=10&skip=0" \
  -H "X-API-Key: dev-api-key-12345"

# ユーザー情報を更新
curl -X PUT "http://localhost:8000/api/v1/admin/users/1" \
  -H "X-API-Key: dev-api-key-12345" \
  -H "Content-Type: application/json" \
  -d '{"email": "updated@example.com", "phone": "+81-90-1234-5678"}'

# OneRosterデータを取得
curl -X GET "http://localhost:8000/api/v1/users" \
  -H "X-API-Key: your-api-key"
```

### データベース管理

#### マイグレーション

```bash
# 新しいマイグレーションファイルの作成
alembic revision --autogenerate -m "migration description"

# マイグレーションの実行
alembic upgrade head

# マイグレーション履歴の確認
alembic history

# 特定のリビジョンまでダウングレード
alembic downgrade <revision_id>
```

#### データベース接続の確認

```bash
# データベースの動作確認
curl -X GET "http://localhost:8000/api/v1/admin/stats" \
  -H "X-API-Key: dev-api-key-12345"
```

この統計エンドポイントが正常に応答すれば、データベース接続が正常に動作しています。

## デプロイメント

### Azureへのデプロイ

本アプリケーションは Microsoft Azure に最適化されており、以下のデプロイメントオプションを提供しています：

#### 自動デプロイメント（推奨）

```bash
# 自動化スクリプトを使用
./scripts/deploy-to-azure.sh prod roster-bridge-jpp japaneast
```

#### 主要なAzureサービス

- **Azure Container Apps**: スケーラブルなコンテナホスティング
- **Azure Database for PostgreSQL**: マネージドデータベース
- **Azure Container Registry**: プライベートコンテナレジストリ
- **Azure Key Vault**: シークレット管理
- **Application Insights**: 監視・ログ・分析

#### サポートドキュメント

- 📖 [Azure デプロイメントガイド](AZURE_DEPLOYMENT.md) - 詳細なデプロイメント手順
- 🔒 [セキュリティハードニングガイド](SECURITY_HARDENING.md) - 本番環境セキュリティ設定
- 🔄 [災害復旧戦略](DISASTER_RECOVERY.md) - バックアップ・復旧手順

#### Infrastructure as Code

Bicepテンプレートを使用したインフラストラクチャの自動プロビジョニング：

```bash
# Bicepを使用したデプロイ
az deployment group create \
  --resource-group rg-roster-bridge-prod \
  --template-file infrastructure/main.bicep \
  --parameters @infrastructure/main.parameters.json
```

#### CI/CD パイプライン

GitHub Actionsによる自動ビルド・デプロイ・テスト：
- 自動テスト実行
- Docker イメージのビルド・プッシュ
- Azure Container Apps への自動デプロイ
- ヘルスチェック・統合テスト
- Slack通知

### ローカル開発環境

#### Docker Compose

```bash
# 開発環境の起動
docker-compose up --build

# データベースのみ起動
docker-compose up -d db
```

## テスト

```bash
# テスト実行
pytest

# カバレッジ付きテスト実行
pytest --cov=app

# 本番環境での統合テスト
pytest app/tests/ -v --env=production
```
