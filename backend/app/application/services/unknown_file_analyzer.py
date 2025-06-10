import logging
import json
import mimetypes
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.domain.external.llm import LLM
from app.application.errors.exceptions import ValidationError, ServerError

logger = logging.getLogger(__name__)


class FileTypeInfo(BaseModel):
    """文件类型信息"""
    filename: str
    mime_type: str
    file_extension: str
    size: int


class FileAnalysisRequest(BaseModel):
    """文件分析请求"""
    file_type_info: FileTypeInfo
    
    
class FileAnalysisResponse(BaseModel):
    """文件分析响应"""
    file_type_description: str
    processing_strategy: str  # command, python_script, binary_analysis, unsupported
    recommended_tools: List[str]
    processing_steps: List[str]
    expected_output: str


class UnknownFileAnalyzer:
    """未知文件类型分析器
    
    使用LLM来分析未知文件类型并提供处理建议
    """
    
    def __init__(self, llm: LLM):
        """初始化分析器
        
        Args:
            llm: LLM接口实例
        """
        self.llm = llm
        logger.info("UnknownFileAnalyzer initialized")
    
    async def analyze_unknown_file_type(self, 
                                      filename: str, 
                                      content_type: Optional[str] = None, 
                                      file_size: int = 0) -> FileAnalysisResponse:
        """分析未知文件类型
        
        Args:
            filename: 文件名
            content_type: MIME类型（可选）
            file_size: 文件大小
            
        Returns:
            FileAnalysisResponse: 分析结果
            
        Raises:
            ValidationError: 输入参数无效
            ServerError: 分析失败
        """
        try:
            # 获取文件扩展名
            file_extension = self._get_file_extension(filename)
            
            # 如果没有提供MIME类型，尝试猜测
            if not content_type:
                content_type = self._guess_mime_type(filename)
            
            # 构建文件类型信息
            file_type_info = FileTypeInfo(
                filename=filename,
                mime_type=content_type,
                file_extension=file_extension,
                size=file_size
            )
            
            # 生成分析提示词
            prompt = self._generate_analysis_prompt(file_type_info)
            
            # 调用LLM进行分析
            messages = [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            # 设置JSON响应格式
            response_format = {
                "type": "json_object"
            }
            
            logger.info(f"Analyzing unknown file type: {filename}")
            llm_response = await self.llm.ask(
                messages=messages,
                response_format=response_format
            )
            
            # 解析LLM响应
            analysis_result = self._parse_llm_response(llm_response)
            
            logger.info(f"Successfully analyzed file type for {filename}: {analysis_result.processing_strategy}")
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing unknown file type {filename}: {str(e)}")
            raise ServerError(f"Failed to analyze file type: {str(e)}")
    
    def _get_file_extension(self, filename: str) -> str:
        """获取文件扩展名"""
        if '.' in filename:
            return '.' + filename.rsplit('.', 1)[1].lower()
        return ''
    
    def _guess_mime_type(self, filename: str) -> str:
        """猜测MIME类型"""
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
    
    def _generate_analysis_prompt(self, file_type_info: FileTypeInfo) -> str:
        """生成分析提示词"""
        return f"""我遇到了一个未知类型的文件，需要你的帮助来确定最佳的处理方案。

文件信息：
- 文件名: {file_type_info.filename}
- MIME类型: {file_type_info.mime_type}
- 文件大小: {file_type_info.size} bytes
- 文件扩展名: {file_type_info.file_extension}

请分析这个文件类型，并提供处理建议。你的回复应该是一个JSON格式，包含以下字段：

1. "file_type_description": 对文件类型的描述
2. "processing_strategy": 处理策略，选择以下之一：
   - "command": 使用命令行工具处理
   - "python_script": 编写Python脚本处理  
   - "binary_analysis": 二进制分析
   - "unsupported": 不支持的文件类型
3. "recommended_tools": 推荐使用的工具或库（数组）
4. "processing_steps": 具体的处理步骤（数组）
5. "expected_output": 期望的输出类型

请直接返回JSON，不要添加任何其他文本。"""
    
    def _parse_llm_response(self, llm_response: Dict[str, Any]) -> FileAnalysisResponse:
        """解析LLM响应"""
        try:
            # 从LLM响应中提取内容
            content = llm_response.get("content", "")
            if not content:
                raise ValidationError("Empty response from LLM")
            
            # 解析JSON
            analysis_data = json.loads(content)
            
            # 验证必需字段
            required_fields = [
                "file_type_description", 
                "processing_strategy", 
                "recommended_tools", 
                "processing_steps", 
                "expected_output"
            ]
            
            for field in required_fields:
                if field not in analysis_data:
                    raise ValidationError(f"Missing required field: {field}")
            
            # 验证processing_strategy的有效值
            valid_strategies = ["command", "python_script", "binary_analysis", "unsupported"]
            if analysis_data["processing_strategy"] not in valid_strategies:
                raise ValidationError(f"Invalid processing strategy: {analysis_data['processing_strategy']}")
            
            # 构建响应对象
            return FileAnalysisResponse(
                file_type_description=analysis_data["file_type_description"],
                processing_strategy=analysis_data["processing_strategy"],
                recommended_tools=analysis_data["recommended_tools"],
                processing_steps=analysis_data["processing_steps"],
                expected_output=analysis_data["expected_output"]
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}")
            raise ValidationError(f"Invalid JSON response from LLM: {str(e)}")
        except Exception as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            raise ValidationError(f"Failed to parse LLM response: {str(e)}") 