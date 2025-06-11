import logging
from typing import List, Dict, Any, Optional, BinaryIO
from datetime import datetime, UTC
from io import BytesIO

from fastapi import UploadFile
from app.domain.models.file import File, FileSource, ProcessingStatus
from app.domain.repositories.file_repository import FileRepository
from app.domain.external.file_processor import FileProcessor, ProcessType
from app.domain.external.llm import LLM
from app.infrastructure.config import get_settings
from app.application.errors.exceptions import NotFoundError, ValidationError, ServerError
from app.application.services.unknown_file_analyzer import UnknownFileAnalyzer

logger = logging.getLogger(__name__)
settings = get_settings()


class FileUploadResponse:
    """文件上传响应"""
    def __init__(self, file_id: str, filename: str, download_url: str, 
                 file_size: int, upload_time: datetime):
        self.file_id = file_id
        self.filename = filename
        self.download_url = download_url
        self.file_size = file_size
        self.upload_time = upload_time


class FileDownloadResponse:
    """文件下载响应"""
    def __init__(self, file_data: bytes, filename: str, content_type: str):
        self.file_data = file_data
        self.filename = filename
        self.content_type = content_type


class FileInfo:
    """文件信息"""
    def __init__(self, file: File):
        self.file_id = file.id
        self.filename = file.filename
        self.original_filename = file.original_filename
        self.file_size = file.file_size
        self.content_type = file.content_type
        self.upload_time = file.upload_time
        self.download_url = f"/api/v1/sessions/{file.session_id}/files/{file.id}/download"
        self.file_type = file.file_type
        self.processing_status = file.processing_status
        self.tags = file.tags
        self.category = file.category
        self.download_count = file.download_count
        self.last_accessed = file.last_accessed
        self.analysis_count = len(file.analysis_results)
        self.process_count = len(file.process_results)


class FileService:
    """
    文件服务
    处理文件的上传、下载、管理等业务逻辑
    """
    
    def __init__(self, 
                 file_repository: FileRepository,
                 file_processor: Optional[FileProcessor] = None,
                 llm: Optional[LLM] = None):
        """
        初始化文件服务
        
        Args:
            file_repository: 文件仓储
            file_processor: 文件处理器（可选）
            llm: LLM接口（可选，用于未知文件类型分析）
        """
        self.file_repository = file_repository
        self.file_processor = file_processor
        self.unknown_file_analyzer = UnknownFileAnalyzer(llm) if llm else None
        logger.info("FileService initialized")
    
    async def upload_file(self, 
                         file: UploadFile,
                         session_id: str,
                         user_id: Optional[str] = None,
                         tags: Optional[List[str]] = None,
                         category: Optional[str] = None) -> FileUploadResponse:
        """
        上传文件
        
        Args:
            file: FastAPI上传文件对象
            session_id: 会话ID
            user_id: 用户ID（可选）
            tags: 标签列表（可选）
            category: 分类（可选）
            
        Returns:
            FileUploadResponse: 上传响应
            
        Raises:
            ValidationError: 文件验证失败
            ServerError: 上传操作失败
        """
        try:
            # 验证文件
            await self._validate_file(file)
            
            # 读取文件内容
            file_data = await file.read()
            
            # 准备元数据
            metadata = {
                "filename": file.filename,
                "original_filename": file.filename,
                "content_type": file.content_type or "application/octet-stream",
                "session_id": session_id,
                "user_id": user_id,
                "upload_source": FileSource.FRONTEND,
                "tags": tags or [],
                "category": category,
                "search_keywords": self._extract_keywords(file.filename)
            }
            
            # 保存文件
            file_id = await self.file_repository.save_file(file_data, metadata)
            
            # 获取文件信息
            file_info = await self.file_repository.get_file_metadata(file_id)
            
            logger.info(f"Successfully uploaded file {file.filename} with ID: {file_id}")
            
            return FileUploadResponse(
                file_id=file_id,
                filename=file_info.filename,
                download_url=f"/api/v1/sessions/{session_id}/files/{file_id}/download",
                file_size=file_info.file_size,
                upload_time=file_info.upload_time
            )
            
        except Exception as e:
            logger.error(f"Error uploading file {file.filename}: {str(e)}")
            raise ServerError(f"Failed to upload file: {str(e)}")
    
    async def download_file(self, file_id: str) -> FileDownloadResponse:
        """
        下载文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            FileDownloadResponse: 下载响应
            
        Raises:
            NotFoundError: 文件不存在
            ServerError: 下载操作失败
        """
        try:
            # 获取文件元数据
            file_info = await self.file_repository.get_file_metadata(file_id)
            if not file_info:
                raise NotFoundError(f"File not found: {file_id}")
            
            # 获取文件内容
            file_data = await self.file_repository.get_file(file_id)
            
            logger.info(f"Successfully downloaded file {file_id}")
            
            return FileDownloadResponse(
                file_data=file_data,
                filename=file_info.filename,
                content_type=file_info.content_type
            )
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise ServerError(f"Failed to download file: {str(e)}")
    
    async def get_file_stream(self, file_id: str) -> tuple[BinaryIO, str, str]:
        """
        获取文件流
        
        Args:
            file_id: 文件ID
            
        Returns:
            tuple: (文件流, 文件名, 内容类型)
            
        Raises:
            NotFoundError: 文件不存在
            ServerError: 操作失败
        """
        try:
            # 获取文件元数据
            file_info = await self.file_repository.get_file_metadata(file_id)
            if not file_info:
                raise NotFoundError(f"File not found: {file_id}")
            
            # 获取文件流
            file_stream = await self.file_repository.get_file_stream(file_id)
            
            logger.info(f"Successfully got file stream for {file_id}")
            
            return file_stream, file_info.filename, file_info.content_type
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting file stream {file_id}: {str(e)}")
            raise ServerError(f"Failed to get file stream: {str(e)}")
    
    async def get_file_history(self, 
                              session_id: Optional[str] = None,
                              user_id: Optional[str] = None,
                              file_type: Optional[str] = None,
                              skip: int = 0,
                              limit: int = 20) -> List[FileInfo]:
        """
        获取文件历史
        
        Args:
            session_id: 会话ID（可选）
            user_id: 用户ID（可选）
            file_type: 文件类型（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[FileInfo]: 文件信息列表
        """
        try:
            # 构建过滤条件
            filters = {}
            if session_id:
                filters["session_id"] = session_id
            if user_id:
                filters["user_id"] = user_id
            if file_type:
                filters["file_type"] = file_type
            
            # 查询文件
            files = await self.file_repository.list_files(
                filters=filters,
                skip=skip,
                limit=limit
            )
            
            # 转换为文件信息
            return [FileInfo(file) for file in files]
            
        except Exception as e:
            logger.error(f"Error getting file history: {str(e)}")
            raise ServerError(f"Failed to get file history: {str(e)}")
    
    async def search_files(self,
                          query: str,
                          session_id: Optional[str] = None,
                          user_id: Optional[str] = None,
                          skip: int = 0,
                          limit: int = 20) -> List[FileInfo]:
        """
        搜索文件
        
        Args:
            query: 搜索查询
            session_id: 会话ID（可选）
            user_id: 用户ID（可选）
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[FileInfo]: 搜索结果
        """
        try:
            # 构建过滤条件
            filters = {}
            if session_id:
                filters["session_id"] = session_id
            if user_id:
                filters["user_id"] = user_id
            
            # 搜索文件
            files = await self.file_repository.search_files(
                query=query,
                filters=filters,
                skip=skip,
                limit=limit
            )
            
            # 转换为文件信息
            return [FileInfo(file) for file in files]
            
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            raise ServerError(f"Failed to search files: {str(e)}")
    
    async def delete_files(self, file_ids: List[str]) -> Dict[str, bool]:
        """
        批量删除文件
        
        Args:
            file_ids: 文件ID列表
            
        Returns:
            Dict[str, bool]: 删除结果
        """
        try:
            results = await self.file_repository.delete_files(file_ids)
            
            success_count = sum(1 for success in results.values() if success)
            logger.info(f"Deleted {success_count}/{len(file_ids)} files")
            
            return results
            
        except Exception as e:
            logger.error(f"Error deleting files: {str(e)}")
            raise ServerError(f"Failed to delete files: {str(e)}")
    
    async def get_file_detail(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件详情
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict[str, Any]: 文件详情
            
        Raises:
            NotFoundError: 文件不存在
        """
        try:
            # 获取文件元数据
            file = await self.file_repository.get_file_metadata(file_id)
            if not file:
                raise NotFoundError(f"File not found: {file_id}")
            
            # 构建详情
            return {
                "file_info": FileInfo(file).__dict__,
                "analysis_history": file.analysis_results,
                "process_history": file.process_results,
                "download_stats": {
                    "download_count": file.download_count,
                    "last_download": file.last_download,
                    "last_accessed": file.last_accessed
                }
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error getting file detail {file_id}: {str(e)}")
            raise ServerError(f"Failed to get file detail: {str(e)}")
    
    async def process_file(self,
                          file_id: str,
                          process_type: ProcessType,
                          options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        处理文件
        
        Args:
            file_id: 文件ID
            process_type: 处理类型
            options: 处理选项
            
        Returns:
            Dict[str, Any]: 处理结果
            
        Raises:
            NotFoundError: 文件不存在
            ServerError: 处理失败
        """
        if not self.file_processor:
            raise ServerError("File processor not configured")
        
        try:
            # 获取文件信息
            file = await self.file_repository.get_file_metadata(file_id)
            if not file:
                raise NotFoundError(f"File not found: {file_id}")
            
            # 更新处理状态
            await self.file_repository.update_file_metadata(
                file_id, 
                {"processing_status": ProcessingStatus.PROCESSING}
            )
            
            # 处理文件
            download_url = f"/api/v1/sessions/{file.session_id}/files/{file_id}/download"
            result = await self.file_processor.process_file(
                download_url=download_url,
                file_id=file_id,
                process_type=process_type,
                options=options
            )
            
            # 更新处理结果
            file.add_process_result(
                process_type=process_type.value,
                result=dict(result),
                processing_time=result.get("processing_time", 0.0)
            )
            
            await self.file_repository.update_file_metadata(
                file_id,
                {
                    "processing_status": ProcessingStatus.COMPLETED,
                    "process_results": [pr.dict() for pr in file.process_results]
                }
            )
            
            logger.info(f"Successfully processed file {file_id} with type {process_type}")
            
            return dict(result)
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error processing file {file_id}: {str(e)}")
            
            # 更新为失败状态
            await self.file_repository.update_file_metadata(
                file_id,
                {"processing_status": ProcessingStatus.FAILED}
            )
            
            raise ServerError(f"Failed to process file: {str(e)}")
    
    async def sync_from_sandbox(self,
                               file_data: bytes,
                               filename: str,
                               session_id: str,
                               metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        从沙盒同步文件
        
        Args:
            file_data: 文件数据
            filename: 文件名
            session_id: 会话ID
            metadata: 额外元数据
            
        Returns:
            str: 文件ID
        """
        try:
            # 准备元数据
            file_metadata = {
                "filename": filename,
                "original_filename": filename,
                "content_type": self._guess_content_type(filename),
                "session_id": session_id,
                "upload_source": FileSource.SANDBOX,
                "is_temporary": True,  # 沙盒文件默认为临时文件
                "search_keywords": self._extract_keywords(filename)
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # 保存文件
            file_id = await self.file_repository.save_file(file_data, file_metadata)
            
            logger.info(f"Successfully synced file {filename} from sandbox with ID: {file_id}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error syncing file from sandbox: {str(e)}")
            raise ServerError(f"Failed to sync file from sandbox: {str(e)}")
    
    async def _validate_file(self, file: UploadFile):
        """
        验证文件
        
        Args:
            file: 上传文件对象
            
        Raises:
            ValidationError: 验证失败
        """
        # 检查文件名
        if not file.filename:
            raise ValidationError("File name is required")
        
        # 检查文件大小
        if file.size and file.size > settings.max_file_size:
            max_size_mb = settings.max_file_size / (1024 * 1024)
            raise ValidationError(f"File size exceeds maximum limit of {max_size_mb}MB")
        
        # 检查文件类型
        content_type = file.content_type or self._guess_content_type(file.filename)
        
        # 如果是已知的允许类型，直接通过
        if content_type in settings.allowed_file_types:
            return
            
        # 如果不允许未知文件类型，则拒绝
        if not settings.allow_unknown_file_types:
            raise ValidationError(f"File type {content_type} is not allowed")
            
        # 对于未知文件类型，记录日志但允许上传
        logger.info(f"Allowing unknown file type: {content_type} for file: {file.filename}")
    
    def _guess_content_type(self, filename: str) -> str:
        """
        根据文件名猜测内容类型
        
        Args:
            filename: 文件名
            
        Returns:
            str: 内容类型
        """
        import mimetypes
        content_type, _ = mimetypes.guess_type(filename)
        return content_type or "application/octet-stream"
    
    def _extract_keywords(self, filename: str) -> List[str]:
        """
        从文件名提取关键词
        
        Args:
            filename: 文件名
            
        Returns:
            List[str]: 关键词列表
        """
        import re
        # 移除扩展名
        name_without_ext = filename.rsplit(".", 1)[0]
        # 分割单词
        words = re.findall(r'\w+', name_without_ext.lower())
        # 过滤短词
        keywords = [w for w in words if len(w) > 2]
        return keywords 
    
    async def analyze_unknown_file_type(self, file_id: str) -> Dict[str, Any]:
        """
        分析未知文件类型
        
        Args:
            file_id: 文件ID
            
        Returns:
            Dict[str, Any]: 分析结果
            
        Raises:
            NotFoundError: 文件不存在
            ServerError: 分析失败
        """
        if not self.unknown_file_analyzer:
            raise ServerError("Unknown file analyzer not available")
        
        try:
            # 获取文件信息
            file = await self.file_repository.get_file_metadata(file_id)
            if not file:
                raise NotFoundError(f"File not found: {file_id}")
            
            # 分析文件类型
            analysis_result = await self.unknown_file_analyzer.analyze_unknown_file_type(
                filename=file.filename,
                content_type=file.content_type,
                file_size=file.file_size
            )
            
            # 将分析结果保存到文件元数据中
            analysis_metadata = {
                "unknown_file_analysis": {
                    "analysis_time": datetime.now(UTC).isoformat(),
                    "file_type_description": analysis_result.file_type_description,
                    "processing_strategy": analysis_result.processing_strategy,
                    "recommended_tools": analysis_result.recommended_tools,
                    "processing_steps": analysis_result.processing_steps,
                    "expected_output": analysis_result.expected_output
                }
            }
            
            await self.file_repository.update_file_metadata(file_id, analysis_metadata)
            
            logger.info(f"Successfully analyzed unknown file type for {file_id}")
            
            return {
                "file_id": file_id,
                "filename": file.filename,
                "analysis": analysis_result.dict()
            }
            
        except NotFoundError:
            raise
        except Exception as e:
            logger.error(f"Error analyzing unknown file type {file_id}: {str(e)}")
            raise ServerError(f"Failed to analyze unknown file type: {str(e)}")