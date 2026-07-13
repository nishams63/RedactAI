"""MinIO / S3 compatible storage client for document management."""
import logging
import os
import socket
import uuid
from typing import Optional
from urllib.parse import urlparse

from core.config import settings

logger = logging.getLogger("redactai.storage")

# MinIO folder prefixes
UPLOAD_PREFIX = "uploads"
OCR_PREFIX = "ocr"
REDACTED_PREFIX = "redacted"
REPORTS_PREFIX = "reports"
TEMP_PREFIX = "temp"

_BACKEND_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_STORAGE_DIR = os.path.join(_BACKEND_ROOT, "local_storage")


def _minio_is_reachable(endpoint: str, timeout: float = 0.3) -> bool:
    """Quick TCP probe to see if MinIO is listening."""
    try:
        parsed = urlparse(endpoint)
        host = parsed.hostname or "localhost"
        port = parsed.port or 9000
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


class StorageClient:
    """Wrapper around boto3 S3 client for MinIO integration.
    
    On init, probes MinIO with a fast TCP check. If unreachable,
    all operations go directly to local filesystem storage — no
    per-request timeout delays.
    """

    def __init__(self):
        self.bucket = settings.MINIO_BUCKET
        if settings.DEPLOYMENT_MODE in ("single", "huggingface"):
            self._minio_online = False
        else:
            self._minio_online = _minio_is_reachable(settings.MINIO_ENDPOINT)
        self.client = None

        if self._minio_online:
            import boto3
            from botocore.config import Config
            config = Config(
                connect_timeout=2,
                read_timeout=5,
                retries={"max_attempts": 0, "mode": "standard"},
            )
            self.client = boto3.client(
                "s3",
                endpoint_url=settings.MINIO_ENDPOINT,
                aws_access_key_id=settings.MINIO_ACCESS_KEY,
                aws_secret_access_key=settings.MINIO_SECRET_KEY,
                region_name="us-east-1",
                config=config,
            )
            logger.info("MinIO is reachable — using S3 storage")
        else:
            logger.warning("MinIO is NOT reachable — using local filesystem storage")

    # ── helpers ──────────────────────────────────────────────────────

    def _local_path(self, key: str) -> str:
        return os.path.join(_LOCAL_STORAGE_DIR, key.replace("/", os.sep))

    def _save_local(self, key: str, content: bytes) -> str:
        path = self._local_path(key)
        try:
            logger.info("BEFORE STEP 5: File save started")
            logger.info(f"Local file write starting for path: {path}")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(content)
            logger.info("AFTER STEP 5: File save started")

            logger.info("BEFORE STEP 6: File save completed")
            logger.info(f"Local file write completed for path: {path}")
            logger.info("AFTER STEP 6: File save completed")
            return f"local://{key}"
        except Exception as e:
            logger.exception("Exception in Step 5 or 6 (local write failure)")
            raise OSError(f"Failed to write to local storage path: {e}")


    # ── public API ───────────────────────────────────────────────────

    def ensure_bucket(self) -> None:
        if not self._minio_online:
            return
        try:
            from botocore.exceptions import ClientError
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            try:
                self.client.create_bucket(Bucket=self.bucket)
                logger.info(f"Created bucket: {self.bucket}")
            except Exception as e:
                logger.warning(f"MinIO bucket setup failed (non-blocking): {e}")

    def upload_file(self, file_content: bytes, document_id: str, filename: str,
                    content_type: str, prefix: str = UPLOAD_PREFIX) -> str:
        key = f"{prefix}/{document_id}/{filename}"
        
        # Step 3: Upload directory resolved
        try:
            logger.info("BEFORE STEP 3: Upload directory resolved")
            dir_path = self._local_path(f"{prefix}/{document_id}")
            logger.info(f"AFTER STEP 3: Upload directory resolved: {dir_path}")
        except Exception as e:
            logger.exception("Exception in Step 3: Upload directory resolved")
            raise e

        # Step 4: Storage provider selected
        try:
            logger.info("BEFORE STEP 4: Storage provider selected")
            provider = "MinIO/S3" if self._minio_online else "Local Filesystem"
            logger.info(f"AFTER STEP 4: Storage provider selected: {provider}")
        except Exception as e:
            logger.exception("Exception in Step 4: Storage provider selected")
            raise e

        if not self._minio_online:
            return self._save_local(key, file_content)

        try:
            logger.info("BEFORE STEP 5: File save started")
            logger.info(f"S3 file write starting for key: {key}")
            self.client.put_object(
                Bucket=self.bucket, Key=key,
                Body=file_content, ContentType=content_type,
            )
            logger.info("AFTER STEP 5: File save started")

            logger.info("BEFORE STEP 6: File save completed")
            logger.info(f"S3 file write completed for key: {key}")
            logger.info("AFTER STEP 6: File save completed")
            return key
        except Exception as e:
            logger.exception("Exception during S3 write (falling back to local filesystem)")
            return self._save_local(key, file_content)



    def download_file(self, storage_path: str) -> Optional[bytes]:
        if storage_path.startswith("local://"):
            key = storage_path.replace("local://", "")
            path = self._local_path(key)
            try:
                with open(path, "rb") as f:
                    return f.read()
            except Exception as e:
                logger.error(f"Local download failed for {storage_path}: {e}")
                return None
        if not self._minio_online:
            return None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=storage_path)
            return response["Body"].read()
        except Exception as e:
            logger.error(f"Download failed for {storage_path}: {e}")
            return None

    def get_presigned_url(self, storage_path: str, expiration: int = 3600) -> Optional[str]:
        if storage_path.startswith("local://"):
            return f"http://localhost:8000/api/v1/documents/local-preview/{storage_path.replace('local://', '')}"
        if not self._minio_online:
            return None
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": storage_path},
                ExpiresIn=expiration,
            )
        except Exception as e:
            logger.error(f"Presigned URL generation failed for {storage_path}: {e}")
            return None

    def delete_file(self, storage_path: str) -> bool:
        if storage_path.startswith("local://"):
            key = storage_path.replace("local://", "")
            path = self._local_path(key)
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Deleted local file: {path}")
                return True
            except Exception as e:
                logger.error(f"Local delete failed for {storage_path}: {e}")
                return False
        if not self._minio_online:
            return False
        try:
            self.client.delete_object(Bucket=self.bucket, Key=storage_path)
            logger.info(f"Deleted {storage_path} from bucket {self.bucket}")
            return True
        except Exception as e:
            logger.error(f"Delete failed for {storage_path}: {e}")
            return False


# Singleton instance
storage_client = StorageClient()
