import os
import tempfile
from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.core.security import verify_api_key
from app.core.config import settings
from app.core.logging import get_logger
from app.services.csv_processor import CSVProcessingService
from app.schemas.oneroster import UploadResponse, EntityType

logger = get_logger(__name__)
router = APIRouter()

# CSV処理サービスの初期化
csv_processor = CSVProcessingService(
    schema_file_path="./oneroster_japan_profile_complete_schema_recreated.json"
)


def process_uploaded_file_background(
    file_path: str,
    entity_type: EntityType,
    db: Session
):
    """バックグラウンドでファイルを処理"""
    try:
        result = csv_processor.process_csv_file(file_path, entity_type, db)
        logger.info(f"Background processing completed for {entity_type.value}: {result}")
    except Exception as e:
        logger.error(f"Background processing failed for {entity_type.value}: {e}")
    finally:
        # 一時ファイルを削除
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/upload", response_model=UploadResponse)
async def upload_csv_files(
    background_tasks: BackgroundTasks,
    academic_sessions: UploadFile = File(None),
    orgs: UploadFile = File(None),
    users: UploadFile = File(None),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """OneRoster Japan Profile形式のCSVファイルをアップロード
    
    Args:
        background_tasks: バックグラウンドタスク
        academic_sessions: 学期・年度CSVファイル
        orgs: 組織CSVファイル 
        users: ユーザーCSVファイル
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        UploadResponse: アップロード結果
    """
    
    uploaded_files = []
    upload_results = {}
    errors = []
    
    # アップロードされたファイルの処理
    file_mapping = {
        EntityType.ACADEMIC_SESSIONS: academic_sessions,
        EntityType.ORGS: orgs,
        EntityType.USERS: users
    }
    
    for entity_type, file in file_mapping.items():
        if file and file.filename:
            try:
                # ファイルサイズチェック
                content = await file.read()
                file_size_mb = len(content) / (1024 * 1024)
                
                if file_size_mb > settings.max_file_size_mb:
                    error_msg = f"{entity_type.value}: ファイルサイズが上限（{settings.max_file_size_mb}MB）を超えています"
                    errors.append(error_msg)
                    continue
                
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.csv',
                    delete=False
                ) as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                # CSV構造の検証
                if not csv_processor.validate_csv_structure(temp_file_path, entity_type):
                    error_msg = f"{entity_type.value}: CSV構造が不正です"
                    errors.append(error_msg)
                    os.remove(temp_file_path)
                    continue
                
                # バックグラウンドでファイル処理
                background_tasks.add_task(
                    process_uploaded_file_background,
                    temp_file_path,
                    entity_type,
                    db
                )
                
                uploaded_files.append(entity_type.value)
                upload_results[entity_type.value] = "処理中"
                
                logger.info(f"File uploaded for processing: {entity_type.value} ({file.filename})")
                
            except Exception as e:
                error_msg = f"{entity_type.value}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing uploaded file {entity_type.value}: {e}")
    
    if not uploaded_files:
        raise HTTPException(
            status_code=400,
            detail="有効なCSVファイルがアップロードされていません"
        )
    
    response = UploadResponse(
        success=len(errors) == 0,
        message=f"{len(uploaded_files)}個のファイルが正常にアップロードされ、処理中です",
        uploaded_count=upload_results,
        errors=errors
    )
    
    logger.info(f"Upload completed: {response.model_dump()}")
    return response


@router.post("/upload-sync", response_model=UploadResponse)
async def upload_csv_files_sync(
    academic_sessions: UploadFile = File(None),
    orgs: UploadFile = File(None),
    users: UploadFile = File(None),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """OneRoster Japan Profile形式のCSVファイルを同期的にアップロード
    
    Args:
        academic_sessions: 学期・年度CSVファイル
        orgs: 組織CSVファイル 
        users: ユーザーCSVファイル
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        UploadResponse: アップロード結果
    """
    
    upload_results = {}
    errors = []
    
    # アップロードされたファイルの処理
    file_mapping = {
        EntityType.ACADEMIC_SESSIONS: academic_sessions,
        EntityType.ORGS: orgs,
        EntityType.USERS: users
    }
    
    for entity_type, file in file_mapping.items():
        if file and file.filename:
            try:
                # ファイルサイズチェック
                content = await file.read()
                file_size_mb = len(content) / (1024 * 1024)
                
                if file_size_mb > settings.max_file_size_mb:
                    error_msg = f"{entity_type.value}: ファイルサイズが上限（{settings.max_file_size_mb}MB）を超えています"
                    errors.append(error_msg)
                    continue
                
                # 一時ファイルに保存
                with tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.csv',
                    delete=False
                ) as temp_file:
                    temp_file.write(content)
                    temp_file_path = temp_file.name
                
                try:
                    # CSV構造の検証
                    if not csv_processor.validate_csv_structure(temp_file_path, entity_type):
                        error_msg = f"{entity_type.value}: CSV構造が不正です"
                        errors.append(error_msg)
                        continue
                    
                    # ファイル処理
                    result = csv_processor.process_csv_file(temp_file_path, entity_type, db)
                    
                    if result['success']:
                        upload_results[entity_type.value] = result['total_processed']
                    else:
                        errors.extend(result.get('errors', [result.get('error', '不明なエラー')]))
                
                finally:
                    # 一時ファイルを削除
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                
                logger.info(f"File processed: {entity_type.value} ({file.filename})")
                
            except Exception as e:
                error_msg = f"{entity_type.value}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error processing uploaded file {entity_type.value}: {e}")
    
    if not upload_results:
        raise HTTPException(
            status_code=400,
            detail="有効なCSVファイルがアップロードされていません"
        )
    
    response = UploadResponse(
        success=len(errors) == 0,
        message=f"{len(upload_results)}個のファイルが正常に処理されました",
        uploaded_count=upload_results,
        errors=errors
    )
    
    logger.info(f"Sync upload completed: {response.model_dump()}")
    return response


@router.post("/csv", response_model=UploadResponse)
async def upload_single_csv_file(
    background_tasks: BackgroundTasks,
    entity_type: EntityType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    """単一のOneRoster Japan Profile形式のCSVファイルをアップロード
    
    Args:
        file: アップロードするCSVファイル
        entity_type: エンティティタイプ（academicSessions、orgs、users）
        background_tasks: バックグラウンドタスク
        db: データベースセッション
        api_key: API認証キー
        
    Returns:
        UploadResponse: アップロード結果
    """
    
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=400,
            detail="CSVファイルをアップロードしてください"
        )
    
    try:
        # ファイルサイズチェック
        content = await file.read()
        file_size_mb = len(content) / (1024 * 1024)
        
        if file_size_mb > settings.max_file_size_mb:
            raise HTTPException(
                status_code=413,
                detail=f"ファイルサイズが上限（{settings.max_file_size_mb}MB）を超えています"
            )
        
        # 一時ファイルに保存
        with tempfile.NamedTemporaryFile(
            mode='wb',
            suffix='.csv',
            delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # CSV構造の検証
        if not csv_processor.validate_csv_structure(temp_file_path, entity_type):
            os.remove(temp_file_path)
            raise HTTPException(
                status_code=400,
                detail=f"CSV構造が{entity_type.value}形式と一致しません"
            )
        
        # バックグラウンドでファイル処理
        background_tasks.add_task(
            process_uploaded_file_background,
            temp_file_path,
            entity_type,
            db
        )
        
        response = UploadResponse(
            success=True,
            message=f"{entity_type.value}ファイル（{file.filename}）が正常にアップロードされ、処理中です",
            uploaded_count={entity_type.value: "処理中"},
            errors=[]
        )
        
        logger.info(f"Single file uploaded for processing: {entity_type.value} ({file.filename})")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading single CSV file: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ファイルアップロードエラー: {str(e)}"
        )
