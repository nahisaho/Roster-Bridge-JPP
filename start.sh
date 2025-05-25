#!/bin/bash

# Roster Bridge API 起動スクリプト

# 環境変数の確認
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
fi

# 仮想環境の確認と作成
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# 仮想環境の有効化
source venv/bin/activate

# 依存関係のインストール
echo "Installing dependencies..."
pip install -r requirements.txt

# データベースマイグレーション
echo "Running database migrations..."
alembic upgrade head

# サーバー起動
echo "Starting Roster Bridge API server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
