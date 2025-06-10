from typing import Optional, Dict, List, Any
from datetime import datetime, UTC
from pydantic import BaseModel, Field
import uuid
from enum import Enum


class FileSource(str, Enum):
    """文件上传来源"""
    FRONTEND = "frontend"
    SANDBOX = "sandbox"


class FileType(str, Enum):
    """文件类型分类"""
    DOCUMENT = "document"
    IMAGE = "image"
    DATA = "data"
    OTHER = "other"


class ProcessingStatus(str, Enum):
    """文件处理状态"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResult(BaseModel):
    """文件分析结果"""
    analysis_type: str
    result: Any
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    model: Optional[str] = None


class ProcessResult(BaseModel):
    """文件处理结果"""
    process_type: str
    result: Dict[str, Any]
    processing_time: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    sandbox_version: Optional[str] = None


class File(BaseModel):
    """
    文件领域模型
    表示系统中的文件实体，包含文件元数据和处理信息
    """
    id: str = Field(default_factory=lambda: uuid.uuid4().hex)  # GridFS文件ID
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    md5_hash: str
    
    # 用户和会话信息
    user_id: Optional[str] = None
    session_id: str
    upload_source: FileSource
    
    # 时间信息
    upload_time: datetime = Field(default_factory=lambda: datetime.now(UTC))
    last_accessed: Optional[datetime] = None
    
    # 分析和处理信息
    analysis_results: List[AnalysisResult] = Field(default_factory=list)
    process_results: List[ProcessResult] = Field(default_factory=list)
    
    # 分类和管理
    file_type: FileType = FileType.OTHER
    processing_status: ProcessingStatus = ProcessingStatus.PENDING
    tags: List[str] = Field(default_factory=list)
    category: Optional[str] = None
    is_temporary: bool = False
    retention_days: int = 30
    
    # 访问控制
    download_count: int = 0
    last_download: Optional[datetime] = None
    
    # 搜索索引
    search_keywords: List[str] = Field(default_factory=list)
    
    # GridFS相关
    gridfs_id: Optional[str] = None  # MongoDB GridFS ObjectId
    download_url: Optional[str] = None
    
    class Config:
        use_enum_values = True
        
    def update_access_info(self):
        """更新文件访问信息"""
        self.last_accessed = datetime.now(UTC)
        self.download_count += 1
        self.last_download = datetime.now(UTC)
        
    def add_analysis_result(self, analysis_type: str, result: Any, model: Optional[str] = None):
        """添加分析结果"""
        analysis = AnalysisResult(
            analysis_type=analysis_type,
            result=result,
            model=model
        )
        self.analysis_results.append(analysis)
        
    def add_process_result(self, process_type: str, result: Dict[str, Any], 
                          processing_time: float, sandbox_version: Optional[str] = None):
        """添加处理结果"""
        process = ProcessResult(
            process_type=process_type,
            result=result,
            processing_time=processing_time,
            sandbox_version=sandbox_version
        )
        self.process_results.append(process)
        self.processing_status = ProcessingStatus.COMPLETED 