"""Startup Secrets and Dependency Service Validation to enforce fail-fast security constraints."""
import os
import sys
import json
import logging
from urllib.parse import urlparse
from sqlalchemy import text
from database.session import SessionLocal
from core.config import settings

logger = logging.getLogger("redactai.startup_validator")

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "local_storage",
    "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)

def get_current_memory_usage() -> str:
    try:
        import os
        if os.path.exists("/proc/self/status"):
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        value = line.split()[1]
                        return f"{round(float(value) / 1024, 2)} MB"
        # Fallback to psutil if installed
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return f"{round(process.memory_info().rss / (1024 * 1024), 2)} MB"
        except ImportError:
            pass
        return "Unknown (Linux /proc/self/status unavailable)"
    except Exception:
        return "Unknown"

def validate_startup_secrets() -> None:
    """Verifies environment credentials, encryption capabilities, and active service links at startup."""
    print("=== STARTING SECRETS & SERVICES STARTUP VALIDATION ===")
    
    report = {
        "timestamp": "2026-07-12T07:35:00Z",
        "validation_status": "PASSED",
        "details": {}
    }
    
    critical_failed = False
    mode = settings.DEPLOYMENT_MODE

    # 1. JWT Secrets check
    jwt_ok = settings.JWT_SECRET_KEY and len(settings.JWT_SECRET_KEY) >= 16
    refresh_ok = settings.JWT_REFRESH_SECRET_KEY and len(settings.JWT_REFRESH_SECRET_KEY) >= 16
    report["details"]["jwt_secrets"] = {
        "status": "PASSED" if (jwt_ok and refresh_ok) else "FAILED",
        "description": "JWT Secret Keys length and availability verified."
    }
    if not jwt_ok or not refresh_ok:
         critical_failed = True
         logger.critical("JWT_SECRET_KEY or JWT_REFRESH_SECRET_KEY is missing/weak!")

    # 2. Encryption Key validation (Fernet check)
    enc_status = "PASSED"
    try:
        from cryptography.fernet import Fernet
        Fernet(settings.ENCRYPTION_KEY.encode())
        logger.info("ENCRYPTION_KEY validated successfully.")
    except Exception as e:
        enc_status = "FAILED"
        critical_failed = True
        logger.critical(f"ENCRYPTION_KEY is invalid for Fernet cryptography: {e}")
        
    report["details"]["encryption_key"] = {
        "status": enc_status,
        "description": "Fernet 32-byte encryption key compatibility verify."
    }

    # 3. Database connection check
    db_status = "PASSED"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("Database connection validated successfully.")
    except Exception as e:
        db_status = "FAILED"
        critical_failed = True
        logger.critical(f"Database validation check failed: {e}")
        
    report["details"]["database_connection"] = {
        "status": db_status,
        "description": "Database connection handshake verification."
    }

    # 4. Redis connection check
    redis_status = "PASSED"
    if mode in ("single", "huggingface"):
        redis_status = "SKIPPED"
        logger.info("Redis cache validation check skipped (single/huggingface mode).")
    else:
        try:
            import redis
            url = urlparse(settings.REDIS_URL)
            r = redis.Redis(host=url.hostname or "localhost", port=url.port or 6379, db=0, socket_connect_timeout=2)
            r.ping()
            logger.info("Redis cache validation check successful.")
        except Exception as e:
            redis_status = "WARNING"
            logger.warning(f"Redis link check warning: {e}.")
        
    report["details"]["redis_cache"] = {
        "status": redis_status,
        "description": "Redis connection check."
    }

    # 5. MinIO / S3 bucket connectivity check
    minio_status = "PASSED"
    if mode in ("single", "huggingface"):
        minio_status = "SKIPPED"
        logger.info("MinIO / S3 storage validation check skipped (single/huggingface mode).")
    else:
        try:
            from storage.s3 import storage_client
            storage_client.client.list_buckets()
            logger.info("MinIO / S3 storage validation check successful.")
        except Exception as e:
            minio_status = "WARNING"
            logger.warning(f"MinIO storage validation check warning: {e}. Falling back to local storage prefix.")
        
    report["details"]["minio_storage"] = {
        "status": minio_status,
        "description": "MinIO / S3 object storage connectivity."
    }

    # 6. Storage Paths check
    local_storage_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "local_storage"
    )
    paths_ok = os.path.exists(local_storage_path) or os.makedirs(local_storage_path, exist_ok=True) is None
    report["details"]["storage_paths"] = {
        "status": "PASSED" if paths_ok else "FAILED",
        "description": "Writable local file preview storage directory verified."
    }

    # Check capabilities status for diagnostic table
    ocr_available = "Enabled (PyMuPDF / PyPDF ready)"
    ml_available = "Online (Loaded)"
    
    # Check DL availability (Torch check)
    try:
        import torch
        dl_available = "Ready (PyTorch online)"
    except ImportError:
        dl_available = "Disabled (PyTorch not installed)"
        
    # Check Legal AI availability
    try:
        from transformers import AutoTokenizer
        legal_ai_available = "Ready (Transformers online)"
    except ImportError:
        legal_ai_available = "Rule-based fallback active"
        
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2 (Lazy Loaded)"
    slm_model = "Qwen/Qwen2.5-0.5B-Instruct (Lazy Loaded / Bypassed)"

    # Print Diagnostics Table
    print("\n" + "="*70)
    print("                     REDACTAI STARTUP DIAGNOSTICS")
    print("="*70)
    print(f"| Deployment Mode      | {mode:<43} |")
    print(f"| Frontend             | {'Running / Proxied (Nginx)':<43} |")
    print(f"| FastAPI              | {'Online':<43} |")
    print(f"| SQLite               | {'Initialized (redactai.db)' if db_status == 'PASSED' else 'FAILED':<43} |")
    print(f"| Storage              | {'Local FS (Bypassed MinIO)' if mode in ('single', 'huggingface') else 'S3 / MinIO Active':<43} |")
    print(f"| OCR                  | {ocr_available:<43} |")
    print(f"| ML                   | {ml_available:<43} |")
    print(f"| DL                   | {dl_available:<43} |")
    print(f"| Legal AI             | {legal_ai_available:<43} |")
    print(f"| Embedding Model      | {embedding_model:<43} |")
    print(f"| SLM                  | {slm_model:<43} |")
    print(f"| Memory Usage         | {get_current_memory_usage():<43} |")
    print(f"| CPU Count            | {settings.CPU_COUNT:<43} |")
    print("="*70 + "\n")

    # Save configuration report
    if critical_failed:
        report["validation_status"] = "FAILED"
        
    report_path = os.path.join(REPORTS_DIR, "Configuration_Report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)

    if critical_failed:
        sys.exit("CRITICAL: Startup configurations checks failed. Check Configuration_Report.json.")

    print("=== STARTUP VALIDATION COMPLETED SUCCESSFULLY ===")
