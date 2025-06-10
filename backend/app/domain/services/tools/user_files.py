from typing import Optional, Dict, Any, List
import httpx
import json
from app.domain.services.tools.base import tool, BaseTool
from app.domain.models.tool_result import ToolResult

class UserFilesTool(BaseTool):
    """用户文件工具，用于查找和处理用户上传的文件"""

    name: str = "user_files"
    
    def __init__(self, backend_url: str = "http://backend:8000", session_id: Optional[str] = None):
        """初始化用户文件工具
        
        Args:
            backend_url: 后端API地址
            session_id: 当前会话ID
        """
        super().__init__()
        self.backend_url = backend_url
        self.session_id = session_id
        
    @tool(
        name="find_user_uploaded_file",
        description="查找用户上传的文件。使用此工具查找用户刚刚上传的文件，按文件名或文件类型搜索。",
        parameters={
            "filename": {
                "type": "string",
                "description": "要查找的文件名（可以是部分匹配）"
            },
            "session_id": {
                "type": "string", 
                "description": "(可选) 会话ID，用于查找特定会话的文件。如果不提供，将使用当前会话。"
            },
            "file_type": {
                "type": "string",
                "description": "(可选) 文件类型：image, document, data, etc."
            },
            "limit": {
                "type": "integer",
                "description": "(可选) 返回结果数量限制，默认为10"
            }
        },
        required=["filename"]
    )
    async def find_user_uploaded_file(
        self,
        filename: str,
        session_id: Optional[str] = None,
        file_type: Optional[str] = None,
        limit: Optional[int] = 10
    ) -> ToolResult:
        """查找用户上传的文件
        
        Args:
            filename: 要查找的文件名
            session_id: 会话ID（如果不提供，使用当前会话）
            file_type: 文件类型
            limit: 结果数量限制
            
        Returns:
            找到的文件信息
        """
        # 如果没有提供session_id，使用存储的session_id
        current_session_id = session_id or self.session_id
        
        try:
            # 构建查询参数
            params = {
                "q": filename,
                "limit": limit or 10
            }
            
            if current_session_id:
                params["session_id"] = current_session_id
                
            # 先尝试搜索文件
            search_url = f"{self.backend_url}/api/v1/files/search"
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(search_url, params=params)
                if resp.status_code == 200:
                    result = resp.json()
                    
                    if result.get("code") == 0:
                        files = result.get("data", {}).get("results", [])
                        
                        if files:
                            # 找到文件，返回详细信息
                            file_info = []
                            for file in files:
                                # 构建完整的下载URL
                                download_url = f"{self.backend_url}{file['download_url']}"
                                
                                file_info.append({
                                    "file_id": file["file_id"],
                                    "filename": file["filename"],
                                    "original_filename": file["original_filename"],
                                    "file_size": file["file_size"],
                                    "content_type": file["content_type"],
                                    "upload_time": file["upload_time"],
                                    "download_url": download_url,
                                    "file_type": file["file_type"],
                                    "tags": file.get("tags", []),
                                    "category": file.get("category")
                                })
                            
                            return ToolResult(
                                success=True,
                                data={
                                    "message": f"找到 {len(files)} 个匹配的文件",
                                    "files": file_info,
                                    "total": len(files)
                                }
                            )
                        else:
                            # 没有找到文件，尝试获取会话的文件历史
                            if current_session_id:
                                history_url = f"{self.backend_url}/api/v1/files/history"
                                history_params = {"session_id": current_session_id, "limit": 20}
                                
                                resp = await client.get(history_url, params=history_params)
                                if resp.status_code == 200:
                                    hist_result = resp.json()
                                    if hist_result.get("code") == 0:
                                        all_files = hist_result.get("data", {}).get("files", [])
                                        
                                        # 在历史中查找匹配的文件名
                                        matching_files = []
                                        for file in all_files:
                                            if filename.lower() in file["filename"].lower():
                                                download_url = f"{self.backend_url}{file['download_url']}"
                                                matching_files.append({
                                                    "file_id": file["file_id"],
                                                    "filename": file["filename"],
                                                    "original_filename": file["original_filename"],
                                                    "file_size": file["file_size"],
                                                    "content_type": file["content_type"],
                                                    "upload_time": file["upload_time"],
                                                    "download_url": download_url,
                                                    "file_type": file["file_type"],
                                                    "tags": file.get("tags", []),
                                                    "category": file.get("category")
                                                })
                                        
                                        if matching_files:
                                            return ToolResult(
                                                success=True,
                                                data={
                                                    "message": f"在会话历史中找到 {len(matching_files)} 个匹配的文件",
                                                    "files": matching_files,
                                                    "total": len(matching_files)
                                                }
                                            )
                                        else:
                                            # 显示会话中的所有文件供参考
                                            recent_files = all_files[:5]  # 显示最近的5个文件
                                            return ToolResult(
                                                success=False,
                                                data={
                                                    "message": f"未找到名为 '{filename}' 的文件。当前会话的最近文件：",
                                                    "recent_files": [f["filename"] for f in recent_files],
                                                    "suggestion": f"请检查文件名是否正确，或者文件是否已上传到当前会话 {current_session_id}"
                                                }
                                            )
                            return ToolResult(
                                success=False,
                                data={
                                    "message": f"未找到名为 '{filename}' 的文件",
                                    "suggestion": "请确认文件名是否正确，或者文件是否已成功上传"
                                }
                            )
                    else:
                        return ToolResult(
                            success=False,
                            data={
                                "message": f"搜索文件时出错: {result.get('msg', 'Unknown error')}",
                                "error_code": result.get("code")
                            }
                        )
                else:
                    return ToolResult(
                        success=False,
                        data={
                            "message": f"无法连接到后端文件服务，状态码: {resp.status_code}",
                            "backend_url": search_url
                        }
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                data={
                    "message": f"查找文件时发生错误: {str(e)}",
                    "error_type": type(e).__name__
                }
            )
    
    @tool(
        name="get_session_files",
        description="获取当前会话的所有上传文件。使用此工具查看用户在当前会话中上传的所有文件。",
        parameters={
            "session_id": {
                "type": "string",
                "description": "会话ID"
            },
            "limit": {
                "type": "integer", 
                "description": "(可选) 返回结果数量限制，默认为20"
            }
        },
        required=["session_id"]
    )
    async def get_session_files(
        self,
        session_id: str,
        limit: Optional[int] = 20
    ) -> ToolResult:
        """获取会话的所有文件
        
        Args:
            session_id: 会话ID
            limit: 结果数量限制
            
        Returns:
            会话中的文件列表
        """
        try:
            history_url = f"{self.backend_url}/api/v1/files/history"
            params = {
                "session_id": session_id,
                "limit": limit or 20
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.get(history_url, params=params)
                if resp.status_code == 200:
                    result = resp.json()
                    
                    if result.get("code") == 0:
                        files = result.get("data", {}).get("files", [])
                        
                        if files:
                            file_list = []
                            for file in files:
                                download_url = f"{self.backend_url}{file['download_url']}"
                                file_list.append({
                                    "file_id": file["file_id"],
                                    "filename": file["filename"],
                                    "original_filename": file["original_filename"],
                                    "file_size": file["file_size"],
                                    "content_type": file["content_type"],
                                    "upload_time": file["upload_time"],
                                    "download_url": download_url,
                                    "file_type": file["file_type"],
                                    "tags": file.get("tags", []),
                                    "category": file.get("category")
                                })
                            
                            return ToolResult(
                                success=True,
                                data={
                                    "message": f"会话 {session_id} 中有 {len(files)} 个文件",
                                    "files": file_list,
                                    "total": len(files)
                                }
                            )
                        else:
                            return ToolResult(
                                success=True,
                                data={
                                    "message": f"会话 {session_id} 中没有上传的文件",
                                    "files": [],
                                    "total": 0
                                }
                            )
                    else:
                        return ToolResult(
                            success=False,
                            data={
                                "message": f"获取文件历史时出错: {result.get('msg', 'Unknown error')}",
                                "error_code": result.get("code")
                            }
                        )
                else:
                    return ToolResult(
                        success=False,
                        data={
                            "message": f"无法连接到后端文件服务，状态码: {resp.status_code}",
                            "backend_url": history_url
                        }
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                data={
                    "message": f"获取会话文件时发生错误: {str(e)}",
                    "error_type": type(e).__name__
                }
            )
    
    @tool(
        name="process_user_file",
        description="处理用户上传的文件。使用此工具分析、提取内容或处理用户文件。",
        parameters={
            "file_id": {
                "type": "string",
                "description": "文件ID"
            },
            "download_url": {
                "type": "string",
                "description": "文件下载URL"
            },
            "process_type": {
                "type": "string",
                "description": "处理类型：analyze_image, extract_text, parse_document, analyze_data"
            },
            "filename": {
                "type": "string",
                "description": "文件名（用于处理）"
            },
            "options": {
                "type": "object",
                "description": "(可选) 处理选项"
            }
        },
        required=["file_id", "download_url", "process_type", "filename"]
    )
    async def process_user_file(
        self,
        file_id: str,
        download_url: str,
        process_type: str,
        filename: str,
        options: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """处理用户文件
        
        Args:
            file_id: 文件ID
            download_url: 下载URL
            process_type: 处理类型
            filename: 文件名
            options: 处理选项
            
        Returns:
            处理结果
        """
        try:
            # 调用沙盒API处理文件
            sandbox_url = "http://localhost:8080/api/v1/files/process"
            
            payload = {
                "download_url": download_url,
                "file_id": file_id,
                "process_type": process_type,
                "options": {
                    "filename": filename,
                    **(options or {})
                }
            }
            
            async with httpx.AsyncClient() as client:
                resp = await client.post(sandbox_url, json=payload)
                if resp.status_code == 200:
                    result = resp.json()
                    
                    if result.get("success"):
                        return ToolResult(
                            success=True,
                            data={
                                "message": f"文件 {filename} 处理成功",
                                "process_type": process_type,
                                "result": result.get("data"),
                                "file_id": file_id
                            }
                        )
                    else:
                        return ToolResult(
                            success=False,
                            data={
                                "message": f"文件处理失败: {result.get('message', 'Unknown error')}",
                                "error": result.get("error")
                            }
                        )
                else:
                    error_text = resp.text
                    return ToolResult(
                        success=False,
                        data={
                            "message": f"沙盒处理失败，状态码: {resp.status_code}",
                            "error": error_text,
                            "sandbox_url": sandbox_url
                        }
                    )
                    
        except Exception as e:
            return ToolResult(
                success=False,
                data={
                    "message": f"处理文件时发生错误: {str(e)}",
                    "error_type": type(e).__name__
                }
            ) 