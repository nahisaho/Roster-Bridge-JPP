import logging
import logging.handlers
import sys
from app.core.config import settings


def setup_logging():
    """ログ設定をセットアップする"""
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.log_level.upper()))
    
    # 既存のハンドラーをクリア
    root_logger.handlers.clear()
    
    # ログフォーマット
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # コンソールハンドラー（開発時用）
    if settings.debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Syslogハンドラー
    try:
        syslog_handler = logging.handlers.SysLogHandler(
            address=(settings.syslog_host, settings.syslog_port),
            facility=settings.syslog_facility
        )
        syslog_handler.setFormatter(formatter)
        root_logger.addHandler(syslog_handler)
    except Exception as e:
        # Syslogが利用できない場合はファイルログに切り替え
        file_handler = logging.FileHandler('roster_bridge.log')
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
        logging.warning(f"Syslog unavailable, using file logging: {e}")


def get_logger(name: str) -> logging.Logger:
    """指定した名前のロガーを取得する"""
    return logging.getLogger(name)
