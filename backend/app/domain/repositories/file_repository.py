from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any, BinaryIO
from app.domain.models.file import File


class FileRepository(ABC):
    """
    文件仓储接口
    定义文件存储的抽象操作
    """
    
    @abstractmethod
    async def save_file(self, file_data: bytes, metadata: Dict[str, Any]) -> str:
        """
        保存文件到存储系统
        
        Args:
            file_data: 文件二进制数据
            metadata: 文件元数据
            
        Returns:
            str: 文件存储ID (GridFS ID)
        """
        pass
    
    @abstractmethod
    async def save_file_stream(self, file_stream: BinaryIO, metadata: Dict[str, Any]) -> str:
        """
        以流的方式保存文件到存储系统
        
        Args:
            file_stream: 文件流
            metadata: 文件元数据
            
        Returns:
            str: 文件存储ID (GridFS ID)
        """
        pass
    
    @abstractmethod
    async def get_file(self, file_id: str) -> bytes:
        """
        根据ID获取文件内容
        
        Args:
            file_id: 文件ID
            
        Returns:
            bytes: 文件二进制数据
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        pass
    
    @abstractmethod
    async def get_file_stream(self, file_id: str) -> BinaryIO:
        """
        根据ID获取文件流
        
        Args:
            file_id: 文件ID
            
        Returns:
            BinaryIO: 文件流
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        pass
    
    @abstractmethod
    async def get_file_metadata(self, file_id: str) -> File:
        """
        根据ID获取文件元数据
        
        Args:
            file_id: 文件ID
            
        Returns:
            File: 文件元数据
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        pass
    
    @abstractmethod
    async def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新文件元数据
        
        Args:
            file_id: 文件ID
            metadata: 要更新的元数据
            
        Returns:
            bool: 更新是否成功
        """
        pass
    
    @abstractmethod
    async def list_files(self, filters: Optional[Dict[str, Any]] = None, 
                        skip: int = 0, limit: int = 20) -> List[File]:
        """
        列出文件
        
        Args:
            filters: 查询过滤条件
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[File]: 文件列表
        """
        pass
    
    @abstractmethod
    async def search_files(self, query: str, filters: Optional[Dict[str, Any]] = None,
                          skip: int = 0, limit: int = 20) -> List[File]:
        """
        搜索文件
        
        Args:
            query: 搜索查询字符串
            filters: 额外的过滤条件
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[File]: 搜索结果
        """
        pass
    
    @abstractmethod
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    @abstractmethod
    async def delete_files(self, file_ids: List[str]) -> Dict[str, bool]:
        """
        批量删除文件
        
        Args:
            file_ids: 文件ID列表
            
        Returns:
            Dict[str, bool]: 每个文件ID对应的删除结果
        """
        pass
    
    @abstractmethod
    async def count_files(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计文件数量
        
        Args:
            filters: 查询过滤条件
            
        Returns:
            int: 文件数量
        """
        pass
    
    @abstractmethod
    async def file_exists(self, file_id: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 文件是否存在
        """
        pass 