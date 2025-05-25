# Alembic データベースマイグレーション設定

# 一般的なPython設定ファイル
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from app.core.config import settings
from app.models.oneroster import Base

# この Alembic の Config オブジェクト
config = context.config

# アプリケーションの設定からデータベースURLを取得
config.set_main_option("sqlalchemy.url", settings.database_url)

# Python ロギングの設定（alembic.ini から）
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLAlchemy MetaData オブジェクト
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """'offline' モードでマイグレーションを実行"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """'online' モードでマイグレーションを実行"""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
