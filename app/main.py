from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.db.database import create_tables
from app.api.v1 import api_router

# ログ設定の初期化
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    # 起動時処理
    logger.info("Starting Roster Bridge API...")
    
    # データベーステーブルの作成
    try:
        create_tables()
        logger.info("Database tables created successfully")
    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise
    
    yield
    
    # 終了時処理
    logger.info("Shutting down Roster Bridge API...")


# FastAPIアプリケーションの作成
app = FastAPI(
    title="Roster Bridge API",
    description="OneRoster Japan Profile形式のCSVファイルを処理するRoster APIサービス",
    version="1.0.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターの登録
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Roster Bridge API",
        "version": "1.0.0",
        "docs": "/docs" if settings.debug else "Disabled in production"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "timestamp": "2025-05-25T00:00:00Z"
    }


# エラーハンドラー
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """HTTPエラーハンドラー"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "status_code": exc.status_code,
                "detail": exc.detail
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """一般的なエラーハンドラー"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "status_code": 500,
                "detail": "Internal server error"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
