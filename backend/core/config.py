import os
from typing import List, Union
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

class Settings(BaseSettings):
    ENVIRONMENT: str = env_name

    # DB & Cache
    DATABASE_URL: str
    REDIS_URL: str

    # MinIO / S3
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "redactai-storage"
    MINIO_SECURE: bool = False

    # JWT & Encryption
    JWT_SECRET_KEY: str
    JWT_REFRESH_SECRET_KEY: str
    ENCRYPTION_KEY: str = "XEfwmtmC9_gIOpoqPIY7kthp84fsSQuhg2IxjAiAB2E=" # default 32-byte Fernet key
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_EXPIRATION_DAYS: int = 0 # 0 means disabled by default
    MAX_ACTIVE_SESSIONS: int = 5
    SESSION_LIMIT_STRATEGY: str = "terminate_oldest" # terminate_oldest or reject_login

    # CORS
    CORS_ORIGINS: Union[str, List[str]] = []

    # Logging
    LOG_LEVEL: str = "INFO"

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
