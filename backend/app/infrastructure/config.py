from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import List


def get_default_allowed_file_types() -> List[str]:
    """获取默认的允许文件类型列表"""
    return [
        # Documents
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "text/html",
        "text/markdown",
        # Images
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/bmp",
        "image/webp",
        # Data files
        "application/json",
        "application/xml",
        "text/csv",
        "application/vnd.ms-excel",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        # Archives
        "application/zip",
        "application/x-rar-compressed",
        "application/x-7z-compressed"
    ]


class Settings(BaseSettings):
    
    # Model provider configuration
    api_key: str | None = None
    api_base: str = "https://api.deepseek.com/v1"
    
    # Model configuration
    model_name: str = "deepseek-chat"
    temperature: float = 0.7
    max_tokens: int = 2000
    
    # MongoDB configuration
    mongodb_uri: str = "mongodb://mongodb:27017"
    mongodb_database: str = "manus"
    mongodb_username: str | None = None
    mongodb_password: str | None = None
    
    # Redis configuration
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    
    # Sandbox configuration
    sandbox_address: str | None = None
    sandbox_image: str | None = None
    sandbox_name_prefix: str | None = None
    sandbox_ttl_minutes: int | None = 30
    sandbox_network: str | None = None  # Docker network bridge name
    sandbox_chrome_args: str | None = ""
    sandbox_https_proxy: str | None = None
    sandbox_http_proxy: str | None = None
    sandbox_no_proxy: str | None = None
    
    # Search engine configuration
    google_search_api_key: str | None = None
    google_search_engine_id: str | None = None
    
    # File upload configuration
    max_file_size: int = 50 * 1024 * 1024  # 50MB
    # 捕获可能存在的环境变量，但不使用它
    allowed_file_types_env: str | None = Field(default=None, alias="allowed_file_types")
    file_retention_days: int = 30
    gridfs_bucket_name: str = "files"
    file_chunk_size: int = 255 * 1024  # 255KB
    
    # 未知文件类型支持
    allow_unknown_file_types: bool = True  # 是否允许上传未知文件类型
    
    # Logging configuration
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        # 允许额外的字段，避免环境变量冲突
        extra = "ignore"
        
    @property
    def allowed_file_types(self) -> List[str]:
        """获取允许的文件类型列表"""
        return get_default_allowed_file_types()
        
    def validate(self):
        if not self.api_key:
            raise ValueError("API key is required")

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    settings.validate()
    return settings 
