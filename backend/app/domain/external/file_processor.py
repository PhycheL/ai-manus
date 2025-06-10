from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from enum import Enum


class ProcessType(str, Enum):
    """文件处理类型"""
    EXTRACT_TEXT = "extract_text"
    ANALYZE_IMAGE = "analyze_image"
    PARSE_DOCUMENT = "parse_document"
    ANALYZE_DATA = "analyze_data"


class FileProcessResult(dict):
    """文件处理结果"""
    def __init__(self, 
                 content: str = "",
                 metadata: Optional[Dict[str, Any]] = None,
                 summary: str = "",
                 key_points: Optional[list] = None,
                 structured_data: Optional[Dict[str, Any]] = None,
                 processing_time: float = 0.0,
                 status: str = "success",
                 error: Optional[str] = None):
        super().__init__(
            content=content,
            metadata=metadata or {},
            summary=summary,
            key_points=key_points or [],
            structured_data=structured_data or {},
            processing_time=processing_time,
            status=status,
            error=error
        )


class FileProcessor(ABC):
    """
    文件处理器接口
    定义文件处理的抽象操作
    """
    
    @abstractmethod
    async def process_file(self, 
                          download_url: str,
                          file_id: str,
                          process_type: ProcessType,
                          options: Optional[Dict[str, Any]] = None) -> FileProcessResult:
        """
        处理文件内容
        
        Args:
            download_url: 文件下载URL
            file_id: 文件ID
            process_type: 处理类型
            options: 处理选项
            
        Returns:
            FileProcessResult: 处理结果
        """
        pass
    
    @abstractmethod
    async def extract_text(self, download_url: str, options: Optional[Dict[str, Any]] = None) -> FileProcessResult:
        """
        提取文件中的文本内容
        
        Args:
            download_url: 文件下载URL
            options: 提取选项
            
        Returns:
            FileProcessResult: 提取结果
        """
        pass
    
    @abstractmethod
    async def analyze_image(self, download_url: str, options: Optional[Dict[str, Any]] = None) -> FileProcessResult:
        """
        分析图片内容
        
        Args:
            download_url: 文件下载URL
            options: 分析选项
            
        Returns:
            FileProcessResult: 分析结果
        """
        pass
    
    @abstractmethod
    async def parse_document(self, download_url: str, options: Optional[Dict[str, Any]] = None) -> FileProcessResult:
        """
        解析文档结构
        
        Args:
            download_url: 文件下载URL
            options: 解析选项
            
        Returns:
            FileProcessResult: 解析结果
        """
        pass
    
    @abstractmethod
    async def analyze_data(self, download_url: str, options: Optional[Dict[str, Any]] = None) -> FileProcessResult:
        """
        分析数据文件
        
        Args:
            download_url: 文件下载URL
            options: 分析选项
            
        Returns:
            FileProcessResult: 分析结果
        """
        pass
    
    @abstractmethod
    async def get_file_type(self, content_type: str, filename: str) -> str:
        """
        判断文件类型
        
        Args:
            content_type: MIME类型
            filename: 文件名
            
        Returns:
            str: 文件类型
        """
        pass 