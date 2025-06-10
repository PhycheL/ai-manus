from typing import Optional, List, Dict, Any
from datetime import datetime, UTC
from beanie import Document, Indexed
from pydantic import Field
import pymongo

from app.domain.models.file import (
    File, FileSource, FileType, ProcessingStatus, 
    AnalysisResult, ProcessResult
)


class FileDocument(Document):
    """
    文件元数据的MongoDB文档模型
    用于存储文件的所有元信息
    """
    # GridFS相关
    gridfs_id: str  # GridFS文件ID
    
    # 基本信息
    filename: Indexed(str)
    original_filename: str
    file_size: int
    content_type: str
    md5_hash: str
    
    # 用户和会话信息
    user_id: Optional[str] = None
    session_id: Indexed(str)
    upload_source: str = FileSource.FRONTEND
    
    # 时间信息
    upload_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_accessed: Optional[datetime] = None
    
    # 分析和处理信息
    analysis_results: List[Dict[str, Any]] = Field(default_factory=list)
    process_results: List[Dict[str, Any]] = Field(default_factory=list)
    
    # 分类和管理
    file_type: str = FileType.OTHER
    processing_status: str = ProcessingStatus.PENDING
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    is_temporary: bool = False
    retention_days: int = 30
    
    # 访问控制
    download_count: int = 0
    last_download: Optional[datetime] = None
    
    # 搜索索引
    search_keywords: List[str] = Field(default_factory=list)
    
    class Settings:
        name = "file_metadata"
        indexes = [
            # 单字段索引
            [("upload_time", pymongo.DESCENDING)],
            [("file_type", pymongo.ASCENDING)],
            [("processing_status", pymongo.ASCENDING)],
            [("user_id", pymongo.ASCENDING)],
            
            # 复合索引
            [
                ("session_id", pymongo.ASCENDING),
                ("upload_time", pymongo.DESCENDING)
            ],
            [
                ("user_id", pymongo.ASCENDING),
                ("upload_time", pymongo.DESCENDING)
            ],
            
            # 文本索引用于搜索
            [
                ("filename", pymongo.TEXT),
                ("original_filename", pymongo.TEXT),
                ("tags", pymongo.TEXT),
                ("search_keywords", pymongo.TEXT)
            ],
        ]
        
        # 启用时间戳
        use_timestamps = True
    
    def to_domain_model(self) -> File:
        """
        转换为领域模型
        
        Returns:
            File: 领域模型实例
        """
        return File(
            id=str(self.id),
            gridfs_id=self.gridfs_id,
            filename=self.filename,
            original_filename=self.original_filename,
            file_size=self.file_size,
            content_type=self.content_type,
            md5_hash=self.md5_hash,
            user_id=self.user_id,
            session_id=self.session_id,
            upload_source=FileSource(self.upload_source),
            upload_time=self.upload_time,
            last_accessed=self.last_accessed,
            analysis_results=[
                AnalysisResult(**result) for result in self.analysis_results
            ],
            process_results=[
                ProcessResult(**result) for result in self.process_results
            ],
            file_type=FileType(self.file_type),
            processing_status=ProcessingStatus(self.processing_status),
            tags=self.tags,
            category=self.category,
            is_temporary=self.is_temporary,
            retention_days=self.retention_days,
            download_count=self.download_count,
            last_download=self.last_download,
            search_keywords=self.search_keywords
        )
    
    def update_access_info(self):
        """更新文件访问信息"""
        self.last_accessed = datetime.now(UTC)
        self.download_count += 1
        self.last_download = datetime.now(UTC)
    
    def add_analysis_result(self, analysis_type: str, result: Any, model: Optional[str] = None):
        """添加分析结果"""
        analysis = {
            "analysis_type": analysis_type,
            "result": result,
            "timestamp": datetime.now(UTC),
            "model": model
        }
        self.analysis_results.append(analysis)
    
    def add_process_result(self, process_type: str, result: Dict[str, Any], 
                          processing_time: float, sandbox_version: Optional[str] = None):
        """添加处理结果"""
        process = {
            "process_type": process_type,
            "result": result,
            "processing_time": processing_time,
            "timestamp": datetime.now(UTC),
            "sandbox_version": sandbox_version
        }
        self.process_results.append(process)
        self.processing_status = ProcessingStatus.COMPLETED 