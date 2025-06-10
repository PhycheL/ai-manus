import logging
from typing import Optional, List, Dict, Any, BinaryIO
from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId

from app.domain.repositories.file_repository import FileRepository
from app.domain.models.file import File, FileSource, FileType, ProcessingStatus
from app.infrastructure.external.file.gridfs_file import GridFSFileService
from app.infrastructure.models.file_document import FileDocument

logger = logging.getLogger(__name__)


class GridFSFileRepository(FileRepository):
    """
    基于GridFS的文件仓储实现
    管理文件的存储和元数据
    """
    
    def __init__(self, database: AsyncIOMotorDatabase):
        """
        初始化仓储
        
        Args:
            database: MongoDB数据库实例
        """
        self.database = database
        self.gridfs_service = GridFSFileService(database)
        # FileDocument将通过Beanie初始化
        
    async def save_file(self, file_data: bytes, metadata: Dict[str, Any]) -> str:
        """
        保存文件到存储系统
        
        Args:
            file_data: 文件二进制数据
            metadata: 文件元数据
            
        Returns:
            str: 文件存储ID (GridFS ID)
        """
        try:
            # 上传文件到GridFS
            gridfs_id = await self.gridfs_service.upload_file(
                file_data=file_data,
                filename=metadata.get("filename", "unknown"),
                content_type=metadata.get("content_type", "application/octet-stream"),
                metadata={
                    "session_id": metadata.get("session_id"),
                    "user_id": metadata.get("user_id"),
                    "upload_source": metadata.get("upload_source", FileSource.FRONTEND)
                }
            )
            
            # 获取GridFS中的文件信息
            file_info = await self.gridfs_service.get_file_info(gridfs_id)
            
            # 创建文件元数据文档
            file_doc = FileDocument(
                gridfs_id=gridfs_id,
                filename=metadata.get("filename", "unknown"),
                original_filename=metadata.get("original_filename", metadata.get("filename", "unknown")),
                file_size=file_info["length"],
                content_type=file_info.get("metadata", {}).get("content_type", "application/octet-stream"),
                md5_hash=file_info.get("metadata", {}).get("md5", ""),
                user_id=metadata.get("user_id"),
                session_id=metadata.get("session_id"),
                upload_source=metadata.get("upload_source", FileSource.FRONTEND),
                file_type=self._determine_file_type(file_info.get("metadata", {}).get("content_type", "")),
                tags=metadata.get("tags", []),
                category=metadata.get("category"),
                is_temporary=metadata.get("is_temporary", False),
                retention_days=metadata.get("retention_days", 30),
                search_keywords=metadata.get("search_keywords", [])
            )
            
            # 保存元数据到数据库
            await file_doc.insert()
            
            logger.info(f"Successfully saved file with ID: {file_doc.id}")
            return str(file_doc.id)
            
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise
    
    async def save_file_stream(self, file_stream: BinaryIO, metadata: Dict[str, Any]) -> str:
        """
        以流的方式保存文件到存储系统
        
        Args:
            file_stream: 文件流
            metadata: 文件元数据
            
        Returns:
            str: 文件存储ID
        """
        try:
            # 上传文件流到GridFS
            gridfs_id = await self.gridfs_service.upload_file_stream(
                file_stream=file_stream,
                filename=metadata.get("filename", "unknown"),
                content_type=metadata.get("content_type", "application/octet-stream"),
                metadata={
                    "session_id": metadata.get("session_id"),
                    "user_id": metadata.get("user_id"),
                    "upload_source": metadata.get("upload_source", FileSource.FRONTEND)
                }
            )
            
            # 获取GridFS中的文件信息
            file_info = await self.gridfs_service.get_file_info(gridfs_id)
            
            # 创建文件元数据文档
            file_doc = FileDocument(
                gridfs_id=gridfs_id,
                filename=metadata.get("filename", "unknown"),
                original_filename=metadata.get("original_filename", metadata.get("filename", "unknown")),
                file_size=file_info["length"],
                content_type=file_info.get("metadata", {}).get("content_type", "application/octet-stream"),
                md5_hash=file_info.get("metadata", {}).get("md5", ""),
                user_id=metadata.get("user_id"),
                session_id=metadata.get("session_id"),
                upload_source=metadata.get("upload_source", FileSource.FRONTEND),
                file_type=self._determine_file_type(file_info.get("metadata", {}).get("content_type", "")),
                tags=metadata.get("tags", []),
                category=metadata.get("category"),
                is_temporary=metadata.get("is_temporary", False),
                retention_days=metadata.get("retention_days", 30),
                search_keywords=metadata.get("search_keywords", [])
            )
            
            # 保存元数据到数据库
            await file_doc.insert()
            
            logger.info(f"Successfully saved file stream with ID: {file_doc.id}")
            return str(file_doc.id)
            
        except Exception as e:
            logger.error(f"Error saving file stream: {str(e)}")
            raise
    
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
        try:
            # 获取文件元数据
            file_doc = await FileDocument.get(file_id)
            if not file_doc:
                raise FileNotFoundError(f"File metadata not found for ID: {file_id}")
            
            # 从GridFS获取文件
            file_data = await self.gridfs_service.download_file(file_doc.gridfs_id)
            
            # 更新访问信息
            file_doc.update_access_info()
            await file_doc.save()
            
            return file_data
            
        except Exception as e:
            logger.error(f"Error getting file {file_id}: {str(e)}")
            raise
    
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
        try:
            # 获取文件元数据
            file_doc = await FileDocument.get(file_id)
            if not file_doc:
                raise FileNotFoundError(f"File metadata not found for ID: {file_id}")
            
            # 从GridFS获取文件流
            file_stream = await self.gridfs_service.download_file_stream(file_doc.gridfs_id)
            
            # 更新访问信息
            file_doc.update_access_info()
            await file_doc.save()
            
            return file_stream
            
        except Exception as e:
            logger.error(f"Error getting file stream {file_id}: {str(e)}")
            raise
    
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
        try:
            # 获取文件元数据
            file_doc = await FileDocument.get(file_id)
            if not file_doc:
                raise FileNotFoundError(f"File metadata not found for ID: {file_id}")
            
            # 转换为领域模型
            return file_doc.to_domain_model()
            
        except Exception as e:
            logger.error(f"Error getting file metadata {file_id}: {str(e)}")
            raise
    
    async def update_file_metadata(self, file_id: str, metadata: Dict[str, Any]) -> bool:
        """
        更新文件元数据
        
        Args:
            file_id: 文件ID
            metadata: 要更新的元数据
            
        Returns:
            bool: 更新是否成功
        """
        try:
            # 获取文件文档
            file_doc = await FileDocument.get(file_id)
            if not file_doc:
                logger.warning(f"File metadata not found for ID: {file_id}")
                return False
            
            # 更新字段
            update_dict = {}
            allowed_fields = [
                "tags", "category", "processing_status", "analysis_results",
                "process_results", "search_keywords", "is_temporary", "retention_days"
            ]
            
            for field in allowed_fields:
                if field in metadata:
                    update_dict[field] = metadata[field]
            
            if update_dict:
                await file_doc.set(update_dict)
                logger.info(f"Successfully updated metadata for file: {file_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating file metadata {file_id}: {str(e)}")
            return False
    
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
        try:
            # 构建查询条件
            query = {}
            if filters:
                for key, value in filters.items():
                    if hasattr(FileDocument, key):
                        query[key] = value
            
            # 查询文档
            file_docs = await FileDocument.find(query).skip(skip).limit(limit).to_list()
            
            # 转换为领域模型
            return [doc.to_domain_model() for doc in file_docs]
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
    
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
        try:
            # 构建文本搜索查询
            search_query = {"$text": {"$search": query}}
            
            # 添加额外过滤条件
            if filters:
                for key, value in filters.items():
                    if hasattr(FileDocument, key):
                        search_query[key] = value
            
            # 执行搜索
            file_docs = await FileDocument.find(search_query).skip(skip).limit(limit).to_list()
            
            # 转换为领域模型
            return [doc.to_domain_model() for doc in file_docs]
            
        except Exception as e:
            logger.error(f"Error searching files: {str(e)}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """
        删除文件
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            # 获取文件元数据
            file_doc = await FileDocument.get(file_id)
            if not file_doc:
                logger.warning(f"File metadata not found for ID: {file_id}")
                return False
            
            # 从GridFS删除文件
            await self.gridfs_service.delete_file(file_doc.gridfs_id)
            
            # 删除元数据
            await file_doc.delete()
            
            logger.info(f"Successfully deleted file: {file_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            return False
    
    async def delete_files(self, file_ids: List[str]) -> Dict[str, bool]:
        """
        批量删除文件
        
        Args:
            file_ids: 文件ID列表
            
        Returns:
            Dict[str, bool]: 每个文件ID对应的删除结果
        """
        results = {}
        
        for file_id in file_ids:
            try:
                results[file_id] = await self.delete_file(file_id)
            except Exception as e:
                logger.error(f"Error deleting file {file_id}: {str(e)}")
                results[file_id] = False
        
        return results
    
    async def count_files(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        统计文件数量
        
        Args:
            filters: 查询过滤条件
            
        Returns:
            int: 文件数量
        """
        try:
            # 构建查询条件
            query = {}
            if filters:
                for key, value in filters.items():
                    if hasattr(FileDocument, key):
                        query[key] = value
            
            # 统计数量
            count = await FileDocument.find(query).count()
            return count
            
        except Exception as e:
            logger.error(f"Error counting files: {str(e)}")
            raise
    
    async def file_exists(self, file_id: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_id: 文件ID
            
        Returns:
            bool: 文件是否存在
        """
        try:
            file_doc = await FileDocument.get(file_id)
            return file_doc is not None
            
        except Exception as e:
            logger.error(f"Error checking file existence {file_id}: {str(e)}")
            return False
    
    def _determine_file_type(self, content_type: str) -> str:
        """
        根据MIME类型判断文件类型
        
        Args:
            content_type: MIME类型
            
        Returns:
            str: 文件类型
        """
        if content_type.startswith("image/"):
            return FileType.IMAGE
        elif content_type in ["application/pdf", "application/msword", 
                             "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                             "text/plain", "text/html", "text/markdown"]:
            return FileType.DOCUMENT
        elif content_type in ["application/json", "application/xml", "text/csv",
                             "application/vnd.ms-excel",
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
            return FileType.DATA
        else:
            return FileType.OTHER 