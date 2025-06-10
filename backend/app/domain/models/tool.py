from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel


class ToolType(str, Enum):
    """工具类型枚举"""
    SEARCH = "search"
    CODE = "code"
    SHELL = "shell"
    VIEW_SHELL = "view_shell"
    VIEW_FILES = "view_files"
    READ_FILE = "read_file"  # 新增：读取文件内容
    ANALYZE_FILE = "analyze_file"  # 新增：分析文件
    SEARCH_IN_FILES = "search_in_files"  # 新增：在文件中搜索
    
    
class Tool(BaseModel):
    """工具基类"""
    name: str
    description: str
    type: ToolType
    parameters: Dict[str, Any]
    
    
class SearchTool(Tool):
    """搜索工具"""
    name: str = "search"
    description: str = "Search for information on the internet"
    type: ToolType = ToolType.SEARCH
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query"
            }
        },
        "required": ["query"]
    }
    

class CodeTool(Tool):
    """代码执行工具"""
    name: str = "code"
    description: str = "Execute Python code in a sandbox environment"
    type: ToolType = ToolType.CODE
    parameters: Dict[str, Any] = {
        "type": "object", 
        "properties": {
            "code": {
                "type": "string",
                "description": "The Python code to execute"
            }
        },
        "required": ["code"]
    }
    

class ShellTool(Tool):
    """Shell命令工具"""
    name: str = "shell"
    description: str = "Execute shell commands in a sandbox environment"
    type: ToolType = ToolType.SHELL
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "command": {
                "type": "string", 
                "description": "The shell command to execute"
            }
        },
        "required": ["command"]
    }


class ViewShellTool(Tool):
    """查看Shell历史工具"""
    name: str = "view_shell"
    description: str = "View shell command execution history in current session"
    type: ToolType = ToolType.VIEW_SHELL
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to view shell history for"
            }
        },
        "required": ["session_id"]
    }


class ViewFilesTool(Tool):
    """查看文件列表工具"""
    name: str = "view_files"
    description: str = "View list of files created in current session"
    type: ToolType = ToolType.VIEW_FILES
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "session_id": {
                "type": "string",
                "description": "The session ID to view files for"
            },
            "path": {
                "type": "string",
                "description": "Optional path to filter files",
                "default": None
            }
        },
        "required": ["session_id"]
    }


class ReadFileTool(Tool):
    """读取文件内容工具"""
    name: str = "read_file"
    description: str = "Read and extract text content from uploaded files"
    type: ToolType = ToolType.READ_FILE
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "The ID of the file to read"
            }
        },
        "required": ["file_id"]
    }


class AnalyzeFileTool(Tool):
    """分析文件工具"""
    name: str = "analyze_file"
    description: str = "Analyze file to extract summary, key points, or metadata"
    type: ToolType = ToolType.ANALYZE_FILE
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "file_id": {
                "type": "string",
                "description": "The ID of the file to analyze"
            },
            "analysis_type": {
                "type": "string",
                "description": "Type of analysis: summary, key_points, metadata",
                "enum": ["summary", "key_points", "metadata"]
            }
        },
        "required": ["file_id", "analysis_type"]
    }


class SearchInFilesTool(Tool):
    """在文件中搜索工具"""
    name: str = "search_in_files"
    description: str = "Search for specific content within uploaded files"
    type: ToolType = ToolType.SEARCH_IN_FILES
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The text to search for in files"
            },
            "file_ids": {
                "type": "array",
                "items": {
                    "type": "string"
                },
                "description": "Optional list of file IDs to search within. If not provided, searches all files",
                "default": None
            }
        },
        "required": ["query"]
    } 