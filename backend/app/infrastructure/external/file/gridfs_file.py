import hashlib
import logging
from datetime import datetime, UTC
from typing import Optional, Dict, Any, BinaryIO, List
from io import BytesIO
from motor.motor_asyncio import AsyncIOMotorGridFSBucket, AsyncIOMotorDatabase
from bson import ObjectId
from bson.errors import InvalidId

logger = logging.getLogger(__name__)


class GridFSFileService:
    """
    GridFS文件存储服务
    提供文件的存储、读取、删除等操作
    """
    
    def __init__(self, database: AsyncIOMotorDatabase, bucket_name: str = "files"):
        """
        初始化GridFS服务
        
        Args:
            database: MongoDB数据库实例
            bucket_name: GridFS bucket名称
        """
        self.database = database
        self.bucket_name = bucket_name
        self._bucket = None
        
    @property
    def bucket(self) -> AsyncIOMotorGridFSBucket:
        """获取GridFS bucket实例"""
        if self._bucket is None:
            self._bucket = AsyncIOMotorGridFSBucket(self.database, bucket_name=self.bucket_name)
        return self._bucket
    
    async def upload_file(self, 
                         file_data: bytes,
                         filename: str,
                         content_type: str,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        上传文件到GridFS
        
        Args:
            file_data: 文件二进制数据
            filename: 文件名
            content_type: 文件MIME类型
            metadata: 额外的元数据
            
        Returns:
            str: GridFS文件ID
        """
        try:
            # 计算文件MD5
            md5_hash = hashlib.md5(file_data).hexdigest()
            
            # 准备元数据
            file_metadata = {
                "filename": filename,
                "content_type": content_type,
                "upload_time": datetime.now(UTC),
                "md5": md5_hash,
                "size": len(file_data)
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # 上传文件
            grid_in = self.bucket.open_upload_stream(
                filename,
                metadata=file_metadata
            )
            
            await grid_in.write(file_data)
            await grid_in.close()
            
            file_id = str(grid_in._id)
            logger.info(f"Successfully uploaded file {filename} with ID: {file_id}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading file {filename}: {str(e)}")
            raise
    
    async def upload_file_stream(self,
                                file_stream: BinaryIO,
                                filename: str,
                                content_type: str,
                                metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        以流的方式上传文件到GridFS
        
        Args:
            file_stream: 文件流
            filename: 文件名
            content_type: 文件MIME类型
            metadata: 额外的元数据
            
        Returns:
            str: GridFS文件ID
        """
        try:
            # 准备元数据
            file_metadata = {
                "filename": filename,
                "content_type": content_type,
                "upload_time": datetime.now(UTC)
            }
            
            if metadata:
                file_metadata.update(metadata)
            
            # 创建MD5计算器
            md5 = hashlib.md5()
            size = 0
            
            # 上传文件
            grid_in = self.bucket.open_upload_stream(
                filename,
                metadata=file_metadata
            )
            
            # 分块读取和上传
            chunk_size = 255 * 1024  # 255KB
            while True:
                chunk = file_stream.read(chunk_size)
                if not chunk:
                    break
                    
                await grid_in.write(chunk)
                md5.update(chunk)
                size += len(chunk)
            
            # 更新元数据
            grid_in.metadata["md5"] = md5.hexdigest()
            grid_in.metadata["size"] = size
            
            await grid_in.close()
            
            file_id = str(grid_in._id)
            logger.info(f"Successfully uploaded file stream {filename} with ID: {file_id}")
            
            return file_id
            
        except Exception as e:
            logger.error(f"Error uploading file stream {filename}: {str(e)}")
            raise
    
    async def download_file(self, file_id: str) -> bytes:
        """
        从GridFS下载文件
        
        Args:
            file_id: GridFS文件ID
            
        Returns:
            bytes: 文件二进制数据
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        try:
            object_id = ObjectId(file_id)
            
            # 检查文件是否存在
            file_doc = await self.bucket.find({"_id": object_id}).to_list(1)
            if not file_doc:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            # 下载文件
            grid_out = await self.bucket.open_download_stream(object_id)
            file_data = await grid_out.read()
            
            logger.info(f"Successfully downloaded file with ID: {file_id}")
            return file_data
            
        except InvalidId:
            raise ValueError(f"Invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error downloading file {file_id}: {str(e)}")
            raise
    
    async def download_file_stream(self, file_id: str) -> BinaryIO:
        """
        从GridFS下载文件流
        
        Args:
            file_id: GridFS文件ID
            
        Returns:
            BinaryIO: 文件流
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        try:
            object_id = ObjectId(file_id)
            
            # 检查文件是否存在
            file_doc = await self.bucket.find({"_id": object_id}).to_list(1)
            if not file_doc:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            # 下载文件到内存流
            grid_out = await self.bucket.open_download_stream(object_id)
            file_stream = BytesIO()
            
            # 分块读取
            chunk_size = 255 * 1024  # 255KB
            while True:
                chunk = await grid_out.readchunk()
                if not chunk:
                    break
                file_stream.write(chunk)
            
            file_stream.seek(0)
            logger.info(f"Successfully downloaded file stream with ID: {file_id}")
            return file_stream
            
        except InvalidId:
            raise ValueError(f"Invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error downloading file stream {file_id}: {str(e)}")
            raise
    
    async def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        获取文件信息
        
        Args:
            file_id: GridFS文件ID
            
        Returns:
            Dict[str, Any]: 文件信息
            
        Raises:
            FileNotFoundError: 文件不存在
        """
        try:
            object_id = ObjectId(file_id)
            
            # 查找文件信息
            file_doc = await self.bucket.find({"_id": object_id}).to_list(1)
            if not file_doc:
                raise FileNotFoundError(f"File with ID {file_id} not found")
            
            file_info = file_doc[0]
            # 转换ObjectId为字符串
            file_info["_id"] = str(file_info["_id"])
            
            return file_info
            
        except InvalidId:
            raise ValueError(f"Invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error getting file info {file_id}: {str(e)}")
            raise
    
    async def delete_file(self, file_id: str) -> bool:
        """
        从GridFS删除文件
        
        Args:
            file_id: GridFS文件ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            object_id = ObjectId(file_id)
            
            # 检查文件是否存在
            file_doc = await self.bucket.find({"_id": object_id}).to_list(1)
            if not file_doc:
                logger.warning(f"File with ID {file_id} not found for deletion")
                return False
            
            # 删除文件
            await self.bucket.delete(object_id)
            logger.info(f"Successfully deleted file with ID: {file_id}")
            return True
            
        except InvalidId:
            raise ValueError(f"Invalid file ID: {file_id}")
        except Exception as e:
            logger.error(f"Error deleting file {file_id}: {str(e)}")
            raise
    
    async def file_exists(self, file_id: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_id: GridFS文件ID
            
        Returns:
            bool: 文件是否存在
        """
        try:
            object_id = ObjectId(file_id)
            file_doc = await self.bucket.find({"_id": object_id}).to_list(1)
            return len(file_doc) > 0
            
        except InvalidId:
            return False
        except Exception as e:
            logger.error(f"Error checking file existence {file_id}: {str(e)}")
            return False
    
    async def list_files(self, 
                        filter_dict: Optional[Dict[str, Any]] = None,
                        skip: int = 0,
                        limit: int = 20) -> List[Dict[str, Any]]:
        """
        列出文件
        
        Args:
            filter_dict: 查询过滤条件
            skip: 跳过的记录数
            limit: 返回的最大记录数
            
        Returns:
            List[Dict[str, Any]]: 文件列表
        """
        try:
            query = filter_dict or {}
            
            # 查询文件
            cursor = self.bucket.find(query).skip(skip).limit(limit)
            files = await cursor.to_list(length=limit)
            
            # 转换ObjectId为字符串
            for file in files:
                file["_id"] = str(file["_id"])
            
            return files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise 