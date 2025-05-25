# 環境設定
cp .env.example .env

# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install -r requirements.txt

# データベースの初期化
alembic upgrade head

# 開発サーバーの起動
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
