import os
import time
import logging
import aiofiles
import aiohttp
import mimetypes
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# 导入文件处理相关的库
import PyPDF2
from PIL import Image
import pandas as pd
import json
import xml.etree.ElementTree as ET
from pathlib import Path

logger = logging.getLogger(__name__)
router = APIRouter(tags=["files"])

# 工作目录
WORKSPACE_DIR = "/tmp/workspace"  # 使用/tmp目录，通常有写权限
DATA_DIR = os.path.join(WORKSPACE_DIR, "data")
SCREENSHOTS_DIR = os.path.join(WORKSPACE_DIR, "screenshots")

# 确保目录存在
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)


class FileProcessRequest(BaseModel):
    """文件处理请求"""
    download_url: str = Field(..., description="文件下载URL")
    file_id: str = Field(..., description="文件ID")
    process_type: str = Field(..., description="处理类型")
    options: Optional[Dict[str, Any]] = Field(default=None, description="处理选项")


class FileProcessResponse(BaseModel):
    """文件处理响应"""
    process_result: Dict[str, Any]
    processing_time: float
    status: str = "success"


class FileSyncRequest(BaseModel):
    """文件同步请求"""
    file_path: str = Field(..., description="文件路径")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="元数据")


class FileDownloadRequest(BaseModel):
    """文件下载请求"""
    download_url: str = Field(..., description="后端文件下载URL")
    file_id: str = Field(..., description="文件ID")
    filename: str = Field(..., description="文件名")
    target_path: Optional[str] = Field(default="/home/ubuntu/", description="目标路径")


@router.post("/process")
async def process_file(request: FileProcessRequest) -> FileProcessResponse:
    """
    处理文件内容
    
    支持的处理类型：
    - extract_text: 提取文本内容
    - analyze_image: 分析图片
    - parse_document: 解析文档结构
    - analyze_data: 分析数据文件
    """
    start_time = time.time()
    
    try:
        # 下载文件
        file_path = await download_file(request.download_url, request.file_id, request.options.get("filename"))
        
        # 根据处理类型处理文件
        if request.process_type == "extract_text":
            result = await extract_text(file_path, request.options)
        elif request.process_type == "analyze_image":
            result = await analyze_image(file_path, request.options)
        elif request.process_type == "parse_document":
            result = await parse_document(file_path, request.options)
        elif request.process_type == "analyze_data":
            result = await analyze_data(file_path, request.options)
        else:
            raise ValueError(f"Unsupported process type: {request.process_type}")
        
        processing_time = time.time() - start_time
        
        return FileProcessResponse(
            process_result=result,
            processing_time=processing_time,
            status="success"
        )
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return FileProcessResponse(
            process_result={"error": str(e)},
            processing_time=time.time() - start_time,
            status="failed"
        )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    target_path: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    上传文件到沙盒
    """
    try:
        # 确定目标路径
        if target_path:
            file_path = os.path.join(WORKSPACE_DIR, target_path)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
        else:
            file_path = os.path.join(DATA_DIR, file.filename)
        
        # 保存文件
        async with aiofiles.open(file_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        logger.info(f"File uploaded to: {file_path}")
        
        return {
            "file_path": file_path,
            "filename": file.filename,
            "file_size": len(content)
        }
        
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/download")
async def download_file(path: str) -> FileResponse:
    """
    从沙盒下载文件
    """
    try:
        print("--------------------sandbox download------------------")
        file_path = os.path.join(WORKSPACE_DIR, path)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type=mimetypes.guess_type(file_path)[0] or "application/octet-stream"
        )
        
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/screenshot")
async def take_screenshot(
    target_path: Optional[str] = Form(None),
    filename: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    截取当前屏幕截图
    """
    try:
        # 生成文件名
        if not filename:
            filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        # 确定保存路径
        if target_path:
            screenshot_path = os.path.join(WORKSPACE_DIR, target_path, filename)
            os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        else:
            screenshot_path = os.path.join(SCREENSHOTS_DIR, filename)
        
        # 使用Selenium或其他工具截图
        # 这里需要集成具体的截图实现
        # 暂时创建一个占位图片
        img = Image.new('RGB', (1920, 1080), color='white')
        img.save(screenshot_path)
        
        logger.info(f"Screenshot saved to: {screenshot_path}")
        
        return {
            "screenshot_path": screenshot_path,
            "filename": filename
        }
        
    except Exception as e:
        logger.error(f"Error taking screenshot: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-to-backend")
async def sync_to_backend(request: FileSyncRequest) -> Dict[str, Any]:
    """
    同步文件到后端存储
    """
    try:
        file_path = os.path.join(WORKSPACE_DIR, request.file_path)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        # 读取文件
        async with aiofiles.open(file_path, 'rb') as f:
            file_data = await f.read()
        
        # 调用后端API保存文件
        # 这里需要从环境变量获取后端地址
        backend_url = os.getenv("BACKEND_URL", "http://backend:8000")
        
        async with aiohttp.ClientSession() as session:
            data = {
                "file_data": file_data,
                "filename": os.path.basename(file_path),
                "session_id": os.getenv("SESSION_ID", ""),
                "metadata": request.metadata or {}
            }
            
            async with session.post(
                f"{backend_url}/api/v1/files/sync-from-sandbox",
                json=data
            ) as resp:
                if resp.status != 200:
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to sync file: {await resp.text()}"
                    )
                
                result = await resp.json()
                return result["data"]
        
    except Exception as e:
        logger.error(f"Error syncing file to backend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/download-from-backend")
async def download_from_backend(request: FileDownloadRequest) -> Dict[str, Any]:
    """
    从后端下载文件到沙箱
    """
    try:
        # 确保目标路径存在
        target_dir = request.target_path.rstrip('/')
        os.makedirs(target_dir, exist_ok=True)
        
        # 构建完整的文件路径
        file_path = os.path.join(target_dir, request.filename)
        
        # 从后端下载文件
        async with aiohttp.ClientSession() as session:
            async with session.get(request.download_url) as resp:
                if resp.status == 200:
                    # 保存文件到本地
                    async with aiofiles.open(file_path, 'wb') as f:
                        async for chunk in resp.content.iter_chunked(8192):
                            await f.write(chunk)
                    
                    # 获取文件大小
                    file_size = os.path.getsize(file_path)
                    
                    logger.info(f"Downloaded file from backend to: {file_path}")
                    
                    return {
                        "success": True,
                        "message": f"文件 {request.filename} 下载成功",
                        "data": {
                            "file_path": file_path,
                            "filename": request.filename,
                            "file_id": request.file_id,
                            "file_size": file_size,
                            "target_path": target_dir
                        }
                    }
                else:
                    raise HTTPException(
                        status_code=resp.status,
                        detail=f"Failed to download file from backend: HTTP {resp.status}"
                    )
        
    except Exception as e:
        logger.error(f"Error downloading file from backend: {str(e)}")
        return {
            "success": False,
            "message": f"下载文件失败: {str(e)}",
            "error": str(e)
        }


# 辅助函数

async def download_file(url: str, file_id: str, filename: Optional[str] = None) -> str:
    """下载文件到本地"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to download file: {resp.status}")
            
            # 如果没有提供文件名，尝试从响应头中提取
            if not filename:
                # 从Content-Disposition头中提取文件名
                content_disposition = resp.headers.get('Content-Disposition', '')
                if 'filename=' in content_disposition:
                    # 解析Content-Disposition: attachment; filename="filename.ext"
                    import re
                    match = re.search(r'filename="([^"]+)"', content_disposition)
                    if match:
                        filename = match.group(1)
                    else:
                        # 处理没有引号的情况
                        match = re.search(r'filename=([^;]+)', content_disposition)
                        if match:
                            filename = match.group(1).strip()
                
                # 如果还是没有文件名，尝试从URL中提取
                if not filename:
                    from urllib.parse import unquote, urlparse
                    parsed_url = urlparse(url)
                    if parsed_url.path:
                        filename = os.path.basename(unquote(parsed_url.path))
                
                # 如果还是没有文件名，使用file_id
                if not filename or filename == '/':
                    filename = f"{file_id}_download"
            
            file_path = os.path.join(DATA_DIR, filename)
            
            async with aiofiles.open(file_path, 'wb') as f:
                async for chunk in resp.content.iter_chunked(8192):
                    await f.write(chunk)
            
            logger.info(f"Downloaded file to: {file_path}")
            return file_path


async def extract_text(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """提取文件中的文本内容"""
    options = options or {}
    content_type = mimetypes.guess_type(file_path)[0]
    
    content = ""
    metadata = {"file_type": content_type}
    
    try:
        if content_type == "application/pdf":
            # 提取PDF文本
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                metadata["pages"] = len(reader.pages)
                
                for page in reader.pages:
                    content += page.extract_text() + "\n"
                    
        elif content_type in ["text/plain", "text/html", "text/markdown"]:
            # 读取文本文件
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                
        else:
            raise ValueError(f"Unsupported file type for text extraction: {content_type}")
        
        # 生成摘要
        summary = content[:500] + "..." if len(content) > 500 else content
        
        return {
            "content": content,
            "metadata": metadata,
            "summary": summary,
            "key_points": [],  # 可以集成NLP提取关键点
            "structured_data": {}
        }
        
    except Exception as e:
        logger.error(f"Error extracting text: {str(e)}")
        raise


async def analyze_image(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """分析图片内容"""
    options = options or {}
    
    try:
        img = Image.open(file_path)
        
        metadata = {
            "format": img.format,
            "mode": img.mode,
            "size": img.size,
            "width": img.width,
            "height": img.height
        }
        
        # 这里可以集成图像识别API
        content = f"Image analysis: {img.width}x{img.height} {img.format} image"
        
        return {
            "content": content,
            "metadata": metadata,
            "summary": content,
            "key_points": [],
            "structured_data": {
                "dimensions": {"width": img.width, "height": img.height},
                "format": img.format
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        raise


async def parse_document(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """解析文档结构"""
    # 这里可以根据文档类型实现更复杂的解析
    return await extract_text(file_path, options)


async def analyze_data(file_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """分析数据文件"""
    options = options or {}
    content_type = mimetypes.guess_type(file_path)[0]
    
    try:
        if content_type == "text/csv":
            # 分析CSV文件
            df = pd.read_csv(file_path)
            
            metadata = {
                "rows": len(df),
                "columns": len(df.columns),
                "column_names": df.columns.tolist()
            }
            
            summary = f"CSV file with {len(df)} rows and {len(df.columns)} columns"
            
            return {
                "content": df.head(10).to_string(),
                "metadata": metadata,
                "summary": summary,
                "key_points": [],
                "structured_data": {
                    "preview": df.head(10).to_dict(),
                    "statistics": df.describe().to_dict() if not df.empty else {}
                }
            }
            
        elif content_type == "application/json":
            # 分析JSON文件
            async with aiofiles.open(file_path, 'r') as f:
                data = json.loads(await f.read())
            
            metadata = {
                "type": type(data).__name__,
                "size": len(str(data))
            }
            
            return {
                "content": json.dumps(data, indent=2)[:1000],
                "metadata": metadata,
                "summary": f"JSON {metadata['type']} with {metadata['size']} characters",
                "key_points": [],
                "structured_data": data if isinstance(data, dict) else {"data": data}
            }
            
        else:
            raise ValueError(f"Unsupported data file type: {content_type}")
            
    except Exception as e:
        logger.error(f"Error analyzing data: {str(e)}")
        raise 