import os
import multiprocessing
from typing import List, Union, Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine environment
env_name = os.getenv("ENVIRONMENT", "development")
env_file_path = f".env.{env_name}"

# If environment variable is passed but we are in a subfolder or running tests,
# we might need to resolve absolute path of env file
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
resolved_env_path = os.path.join(parent_dir, env_file_path)

# Resource Detection
cpu_count = multiprocessing.cpu_count()
memory_bytes = 0
try:
    memory_bytes = os.sysconf('SC_PAGE_SIZE') * os.sysconf('SC_PHYS_PAGES')
except (AttributeError, ValueError):
    try:
        import ctypes
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ('dwLength', ctypes.c_ulong),
                ('dwMemoryLoad', ctypes.c_ulong),
                ('ullTotalPhys', ctypes.c_ulonglong),
                ('ullAvailPhys', ctypes.c_ulonglong),
                ('ullTotalPageFile', ctypes.c_ulonglong),
                ('ullAvailPageFile', ctypes.c_ulonglong),
                ('ullTotalVirtual', ctypes.c_ulonglong),
                ('ullAvailVirtual', ctypes.c_ulonglong),
                ('ullAvailExtendedVirtual', ctypes.c_ulonglong),
            ]
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        memory_bytes = stat.ullTotalPhys
    except Exception:
        memory_bytes = 8 * 1024 * 1024 * 1024  # Default 8GB

ram_mb = memory_bytes / (1024 * 1024)
low_resource_mode = ram_mb < 4096 or cpu_count < 2

class Settings(BaseSettings):
    ENVIRONMENT: str = env_name
    DEPLOYMENT_MODE: str = os.getenv("DEPLOYMENT_MODE", "production")  # development, production, single, huggingface
    
    # Resource constraints metadata
    RAM_MB: float = ram_mb
    CPU_COUNT: int = cpu_count
    LOW_RESOURCE_MODE: bool = low_resource_mode

    # DB & Cache
    DATABASE_URL: Optional[str] = None
    REDIS_URL: Optional[str] = None

    # MinIO / S3
    MINIO_ENDPOINT: Optional[str] = None
    MINIO_ACCESS_KEY: Optional[str] = None
    MINIO_SECRET_KEY: Optional[str] = None
    MINIO_BUCKET: str = "redactai-storage"
    MINIO_SECURE: bool = False
    BACKEND_URL: str = os.getenv("RENDER_EXTERNAL_URL", os.getenv("BACKEND_URL", "http://localhost:8000"))
    LOCAL_STORAGE_DIR: str = ""

    # JWT & Encryption
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ENCRYPTION_KEY: str = "XEfwmtmC9_gIOpoqPIY7kthp84fsSQuhg2IxjAiAB2E=" # default 32-byte Fernet key
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_EXPIRATION_DAYS: int = 0 # 0 means disabled by default
    MAX_ACTIVE_SESSIONS: int = 5
    SESSION_LIMIT_STRATEGY: str = "terminate_oldest" # terminate_oldest or reject_login

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def default_database_url(cls, v: Optional[str]) -> Optional[str]:
        mode = os.getenv("DEPLOYMENT_MODE", "production")
        if not v or mode in ("single", "huggingface"):
            return "sqlite:///./redactai.db"
        return v

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def default_redis_url(cls, v: Optional[str]) -> Optional[str]:
        mode = os.getenv("DEPLOYMENT_MODE", "production")
        if not v or mode in ("single", "huggingface"):
            return ""
        return v

    @field_validator("LOCAL_STORAGE_DIR", mode="before")
    @classmethod
    def default_local_storage_dir(cls, v: Optional[str]) -> str:
        if not v:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            parent_dir = os.path.dirname(current_dir)
            return os.path.join(parent_dir, "local_storage")
        return v

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = []
    ALLOWED_HOSTS: Union[str, List[str]] = ["*"]

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("ALLOWED_HOSTS", mode="before")
    @classmethod
    def assemble_allowed_hosts(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, str) and v.startswith("["):
            import json
            try:
                return json.loads(v)
            except Exception:
                return [v]
        return v

    model_config = SettingsConfigDict(
        env_file=resolved_env_path,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
