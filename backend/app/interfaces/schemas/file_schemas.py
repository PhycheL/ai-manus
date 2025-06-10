from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class FileUploadResponse(BaseModel):
    """文件上传响应"""
    file_id: str
    filename: str
    download_url: str
    file_size: int
    upload_time: datetime


class FileInfo(BaseModel):
    """文件信息"""
    file_id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    upload_time: datetime
    download_url: str
    file_type: str
    processing_status: str
    tags: List[str]
    category: Optional[str]
    download_count: int
    last_accessed: Optional[datetime]
    analysis_count: Optional[int] = 0
    process_count: Optional[int] = 0


class FileHistoryResponse(BaseModel):
    """文件历史响应"""
    files: List[FileInfo]
    total: int
    page: int


class FileSearchResult(BaseModel):
    """文件搜索结果"""
    file_id: str
    filename: str
    original_filename: str
    file_size: int
    content_type: str
    upload_time: datetime
    download_url: str
    file_type: str
    processing_status: str
    tags: List[str]
    category: Optional[str]
    download_count: int
    last_accessed: Optional[datetime]


class FileSearchResponse(BaseModel):
    """文件搜索响应"""
    results: List[FileSearchResult]
    total: int


class FileDetailResponse(BaseModel):
    """文件详情响应"""
    file_info: Dict[str, Any]
    analysis_history: List[Dict[str, Any]]
    process_history: List[Dict[str, Any]]
    download_stats: Dict[str, Any]


class FileProcessRequest(BaseModel):
    """文件处理请求"""
    process_type: str = Field(..., description="处理类型")
    options: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="处理选项"
    )


class FileProcessResponse(BaseModel):
    """文件处理响应"""
    file_id: str
    process_type: str
    process_result: Dict[str, Any]


class FileSyncRequest(BaseModel):
    """文件同步请求"""
    file_data: bytes = Field(..., description="文件数据")
    filename: str = Field(..., description="文件名")
    session_id: str = Field(..., description="会话ID")
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="额外元数据"
    )


class FileSyncResponse(BaseModel):
    """文件同步响应"""
    file_id: str
    download_url: str


class FileDeleteRequest(BaseModel):
    """文件删除请求"""
    file_ids: List[str] = Field(..., description="要删除的文件ID列表") 