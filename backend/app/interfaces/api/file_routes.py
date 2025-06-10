from fastapi import APIRouter, Depends, UploadFile, File, Form, Query, Response
from fastapi.responses import StreamingResponse
from typing import List, Optional, Dict, Any
import logging

from app.application.services.file_service import FileService
from app.interfaces.schemas.response import APIResponse
from app.interfaces.schemas.file_schemas import (
    FileUploadResponse,
    FileHistoryResponse,
    FileSearchResponse,
    FileDetailResponse,
    FileProcessRequest,
    FileProcessResponse,
    FileSyncRequest,
    FileSyncResponse,
    FileDeleteRequest,
    FileAnalysisResult
)
from app.domain.external.file_processor import ProcessType

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/files", tags=["files"])


def get_file_service() -> FileService:
    # This will be overridden by dependency injection
    # If you see this error, dependency injection is not working
    raise RuntimeError("FileService dependency injection not configured")


@router.post("/upload", response_model=APIResponse[FileUploadResponse])
async def upload_file(
    file: UploadFile = File(...),
    session_id: str = Form(...),
    user_id: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # 逗号分隔的标签
    category: Optional[str] = Form(None),
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileUploadResponse]:
    """
    上传文件
    
    支持的文件类型：
    - 文档：PDF, Word, TXT, HTML, Markdown
    - 图片：JPEG, PNG, GIF, BMP, WebP
    - 数据：JSON, XML, CSV, Excel
    - 压缩包：ZIP, RAR, 7Z
    
    文件大小限制：50MB
    """
    try:
        # 解析标签
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else None
        
        print(f"---------------------------------Uploading file: {file.filename} to session: {session_id}")  
        # 上传文件
        result = await file_service.upload_file(
            file=file,
            session_id=session_id,
            user_id=user_id,
            tags=tag_list,
            category=category
        )
        
        return APIResponse.success(
            FileUploadResponse(
                file_id=result.file_id,
                filename=result.filename,
                download_url=result.download_url,
                file_size=result.file_size,
                upload_time=result.upload_time
            )
        )
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise


@router.get("/{file_id}/download")
async def download_file(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
) -> StreamingResponse:
    """
    下载文件
    
    返回文件流，支持断点续传
    """
    try:
        # 获取文件流
        file_stream, filename, content_type = await file_service.get_file_stream(file_id)
        
        # 返回流式响应
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        logger.error(f"Error downloading file {file_id}: {str(e)}")
        raise


@router.get("/history", response_model=APIResponse[FileHistoryResponse])
async def get_file_history(
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    file_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileHistoryResponse]:
    """
    获取文件历史
    
    支持按会话、用户、文件类型过滤
    """
    try:
        files = await file_service.get_file_history(
            session_id=session_id,
            user_id=user_id,
            file_type=file_type,
            skip=skip,
            limit=limit
        )
        
        return APIResponse.success(
            FileHistoryResponse(
                files=[{
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "original_filename": f.original_filename,
                    "file_size": f.file_size,
                    "content_type": f.content_type,
                    "upload_time": f.upload_time,
                    "download_url": f.download_url,
                    "file_type": f.file_type,
                    "processing_status": f.processing_status,
                    "tags": f.tags,
                    "category": f.category,
                    "download_count": f.download_count,
                    "last_accessed": f.last_accessed,
                    "analysis_count": f.analysis_count,
                    "process_count": f.process_count
                } for f in files],
                total=len(files),
                page=skip // limit + 1
            )
        )
        
    except Exception as e:
        logger.error(f"Error getting file history: {str(e)}")
        raise


@router.get("/search", response_model=APIResponse[FileSearchResponse])
async def search_files(
    q: str = Query(..., min_length=1),
    session_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileSearchResponse]:
    """
    搜索文件
    
    支持文件名、标签、关键词搜索
    """
    try:
        files = await file_service.search_files(
            query=q,
            session_id=session_id,
            user_id=user_id,
            skip=skip,
            limit=limit
        )
        
        return APIResponse.success(
            FileSearchResponse(
                results=[{
                    "file_id": f.file_id,
                    "filename": f.filename,
                    "original_filename": f.original_filename,
                    "file_size": f.file_size,
                    "content_type": f.content_type,
                    "upload_time": f.upload_time,
                    "download_url": f.download_url,
                    "file_type": f.file_type,
                    "processing_status": f.processing_status,
                    "tags": f.tags,
                    "category": f.category,
                    "download_count": f.download_count,
                    "last_accessed": f.last_accessed
                } for f in files],
                total=len(files)
            )
        )
        
    except Exception as e:
        logger.error(f"Error searching files: {str(e)}")
        raise


@router.get("/{file_id}/detail", response_model=APIResponse[FileDetailResponse])
async def get_file_detail(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileDetailResponse]:
    """
    获取文件详情
    
    包含文件信息、分析历史、处理历史等
    """
    try:
        detail = await file_service.get_file_detail(file_id)
        
        return APIResponse.success(
            FileDetailResponse(**detail)
        )
        
    except Exception as e:
        logger.error(f"Error getting file detail {file_id}: {str(e)}")
        raise


@router.delete("/batch", response_model=APIResponse[Dict[str, bool]])
async def delete_files(
    request: FileDeleteRequest,
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[Dict[str, bool]]:
    """
    批量删除文件
    
    返回每个文件的删除结果
    """
    try:
        results = await file_service.delete_files(request.file_ids)
        
        return APIResponse.success(results)
        
    except Exception as e:
        logger.error(f"Error deleting files: {str(e)}")
        raise


@router.post("/{file_id}/process", response_model=APIResponse[FileProcessResponse])
async def process_file(
    file_id: str,
    request: FileProcessRequest,
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileProcessResponse]:
    """
    处理文件
    
    支持的处理类型：
    - extract_text: 提取文本内容
    - analyze_image: 分析图片
    - parse_document: 解析文档结构
    - analyze_data: 分析数据文件
    """
    try:
        result = await file_service.process_file(
            file_id=file_id,
            process_type=ProcessType(request.process_type),
            options=request.options
        )
        
        return APIResponse.success(
            FileProcessResponse(
                file_id=file_id,
                process_type=request.process_type,
                process_result=result
            )
        )
        
    except Exception as e:
        logger.error(f"Error processing file {file_id}: {str(e)}")
        raise


@router.post("/sync-from-sandbox", response_model=APIResponse[FileSyncResponse])
async def sync_from_sandbox(
    request: FileSyncRequest,
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileSyncResponse]:
    """
    从沙盒同步文件
    
    用于保存沙盒中生成的文件
    """
    try:
        file_id = await file_service.sync_from_sandbox(
            file_data=request.file_data,
            filename=request.filename,
            session_id=request.session_id,
            metadata=request.metadata
        )
        
        download_url = f"/api/v1/files/{file_id}/download"
        
        return APIResponse.success(
            FileSyncResponse(
                file_id=file_id,
                download_url=download_url
            )
        )
        
    except Exception as e:
        logger.error(f"Error syncing file from sandbox: {str(e)}")
        raise


@router.post("/{file_id}/analyze-unknown-type", response_model=APIResponse[FileAnalysisResult])
async def analyze_unknown_file_type(
    file_id: str,
    file_service: FileService = Depends(get_file_service)
) -> APIResponse[FileAnalysisResult]:
    """
    分析未知文件类型
    
    使用LLM分析未知文件类型，并提供处理建议
    """
    try:
        result = await file_service.analyze_unknown_file_type(file_id)
        
        return APIResponse.success(
            FileAnalysisResult(
                file_id=result["file_id"],
                filename=result["filename"],
                analysis=result["analysis"]
            )
        )
        
    except Exception as e:
        logger.error(f"Error analyzing unknown file type {file_id}: {str(e)}")
        raise 