import logging
from typing import Optional, Dict, Any, List
from app.domain.repositories.file_repository import FileRepository
from app.domain.external.file_processor import FileProcessor, ProcessType
from app.domain.models.file import File

logger = logging.getLogger(__name__)


class FileContentTool:
    """
    文件内容工具
    供Agent使用的文件处理工具
    """
    
    def __init__(self, 
                 file_repository: FileRepository,
                 file_processor: Optional[FileProcessor] = None):
        """
        初始化文件内容工具
        
        Args:
            file_repository: 文件仓储
            file_processor: 文件处理器
        """
        self.file_repository = file_repository
        self.file_processor = file_processor
        
    async def read_file_content(self, file_id: str) -> str:
        """
        读取文件内容
        
        Args:
            file_id: 文件ID
            
        Returns:
            str: 文件内容（文本格式）
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的文件类型
        """
        try:
            # 获取文件元数据
            file = await self.file_repository.get_file_metadata(file_id)
            if not file:
                raise FileNotFoundError(f"File not found: {file_id}")
            
            # 检查是否已有处理结果
            for result in file.process_results:
                if result.process_type == ProcessType.EXTRACT_TEXT:
                    content = result.result.get("content", "")
                    if content:
                        logger.info(f"Using cached text content for file {file_id}")
                        return content
            
            # 如果没有缓存的文本内容，则处理文件
            if self.file_processor:
                logger.info(f"Processing file {session_id}: {file_id} to extract text")
                download_url = f"/api/v1/sessions/{session_id}/files/{file_id}/download"
                
                process_result = await self.file_processor.process_file(
                    download_url=download_url,
                    file_id=file_id,
                    process_type=ProcessType.EXTRACT_TEXT
                )
                
                # 保存处理结果
                file.add_process_result(
                    process_type=ProcessType.EXTRACT_TEXT,
                    result=dict(process_result),
                    processing_time=process_result.get("processing_time", 0.0)
                )
                
                # 更新文件元数据
                await self.file_repository.update_file_metadata(
                    file_id,
                    {"process_results": [pr.dict() for pr in file.process_results]}
                )
                
                return process_result.get("content", "")
            
            # 如果没有处理器，尝试直接读取文本文件
            if file.content_type in ["text/plain", "text/html", "text/markdown"]:
                file_data = await self.file_repository.get_file(file_id)
                return file_data.decode("utf-8", errors="ignore")
            
            raise ValueError(f"Cannot read content from file type: {file.content_type}")
            
        except Exception as e:
            logger.error(f"Error reading file content {file_id}: {str(e)}")
            raise
    
    async def analyze_file(self, file_id: str, analysis_type: str) -> Dict[str, Any]:
        """
        分析文件
        
        Args:
            file_id: 文件ID
            analysis_type: 分析类型
            
        Returns:
            Dict[str, Any]: 分析结果
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 不支持的分析类型
        """
        try:
            # 获取文件元数据
            file = await self.file_repository.get_file_metadata(file_id)
            if not file:
                raise FileNotFoundError(f"File not found: {file_id}")
            
            # 检查是否已有分析结果
            for result in file.analysis_results:
                if result.analysis_type == analysis_type:
                    logger.info(f"Using cached analysis for file {file_id}, type: {analysis_type}")
                    return result.result
            
            # 根据分析类型执行分析
            if analysis_type == "summary":
                content = await self.read_file_content(file_id)
                # 这里可以集成LLM生成摘要
                summary = self._generate_summary(content)
                result = {"summary": summary}
                
            elif analysis_type == "key_points":
                content = await self.read_file_content(file_id)
                # 提取关键点
                key_points = self._extract_key_points(content)
                result = {"key_points": key_points}
                
            elif analysis_type == "metadata":
                # 返回文件元数据
                result = {
                    "filename": file.filename,
                    "file_type": file.file_type,
                    "file_size": file.file_size,
                    "content_type": file.content_type,
                    "upload_time": file.upload_time.isoformat(),
                    "tags": file.tags,
                    "category": file.category
                }
                
            else:
                raise ValueError(f"Unsupported analysis type: {analysis_type}")
            
            # 保存分析结果
            file.add_analysis_result(
                analysis_type=analysis_type,
                result=result
            )
            
            # 更新文件元数据
            await self.file_repository.update_file_metadata(
                file_id,
                {"analysis_results": [ar.dict() for ar in file.analysis_results]}
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_id}: {str(e)}")
            raise
    
    async def search_in_files(self, query: str, file_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        在文件中搜索
        
        Args:
            query: 搜索查询
            file_ids: 限定搜索的文件ID列表（可选）
            
        Returns:
            List[Dict[str, Any]]: 搜索结果
        """
        try:
            results = []
            
            # 如果没有指定文件ID，则搜索所有文件
            if not file_ids:
                files = await self.file_repository.search_files(query)
                file_ids = [f.id for f in files]
            
            # 在每个文件中搜索
            for file_id in file_ids:
                try:
                    content = await self.read_file_content(file_id)
                    if query.lower() in content.lower():
                        # 提取包含查询的片段
                        snippets = self._extract_snippets(content, query)
                        
                        file = await self.file_repository.get_file_metadata(file_id)
                        results.append({
                            "file_id": file_id,
                            "filename": file.filename,
                            "snippets": snippets,
                            "relevance_score": len(snippets)
                        })
                except Exception as e:
                    logger.warning(f"Error searching in file {file_id}: {str(e)}")
                    continue
            
            # 按相关性排序
            results.sort(key=lambda x: x["relevance_score"], reverse=True)
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching in files: {str(e)}")
            raise
    
    def _generate_summary(self, content: str, max_length: int = 500) -> str:
        """
        生成文本摘要
        
        Args:
            content: 文本内容
            max_length: 最大长度
            
        Returns:
            str: 摘要
        """
        # 简单的摘要生成，实际应用中可以使用LLM
        lines = content.split('\n')
        summary_lines = []
        current_length = 0
        
        for line in lines:
            line = line.strip()
            if line and current_length + len(line) <= max_length:
                summary_lines.append(line)
                current_length += len(line)
            elif current_length >= max_length:
                break
        
        summary = ' '.join(summary_lines)
        if len(content) > len(summary):
            summary += "..."
            
        return summary
    
    def _extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """
        提取关键点
        
        Args:
            content: 文本内容
            max_points: 最大关键点数
            
        Returns:
            List[str]: 关键点列表
        """
        # 简单的关键点提取，实际应用中可以使用NLP技术
        lines = content.split('\n')
        key_points = []
        
        for line in lines:
            line = line.strip()
            # 查找包含关键词的行
            if any(keyword in line.lower() for keyword in ['important', 'key', 'main', 'summary', '重要', '关键', '主要']):
                key_points.append(line)
                if len(key_points) >= max_points:
                    break
        
        # 如果没有找到关键词，返回前几行非空行
        if not key_points:
            for line in lines[:max_points]:
                line = line.strip()
                if line:
                    key_points.append(line)
        
        return key_points
    
    def _extract_snippets(self, content: str, query: str, context_size: int = 100) -> List[str]:
        """
        提取包含查询的文本片段
        
        Args:
            content: 文本内容
            query: 查询字符串
            context_size: 上下文大小
            
        Returns:
            List[str]: 文本片段列表
        """
        snippets = []
        content_lower = content.lower()
        query_lower = query.lower()
        
        # 查找所有匹配位置
        start = 0
        while True:
            pos = content_lower.find(query_lower, start)
            if pos == -1:
                break
            
            # 提取上下文
            snippet_start = max(0, pos - context_size)
            snippet_end = min(len(content), pos + len(query) + context_size)
            
            snippet = content[snippet_start:snippet_end]
            if snippet_start > 0:
                snippet = "..." + snippet
            if snippet_end < len(content):
                snippet = snippet + "..."
                
            snippets.append(snippet)
            start = pos + 1
            
            # 限制片段数量
            if len(snippets) >= 5:
                break
        
        return snippets 