"""Operational readiness, liveness, dependencies, versioning and reports download routes."""
import os
import json
import time
import socket
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from dependencies import get_db, get_current_user
from models.user import User
from services.legal_ai.security_checker import REPORTS_DIR

router = APIRouter(prefix="/release", tags=["Release Operations"])

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "RELEASE_MANIFEST.json"
)

def _is_service_reachable(url_str: str, default_port: int) -> bool:
    try:
        url = urlparse(url_str)
        host = url.hostname or "localhost"
        port = url.port or default_port
        
        # Guard: synchronous DNS getaddrinfo resolution on Windows host blocks for unresolved Docker names
        if os.name == 'nt' and host in ["redis", "db", "minio"]:
            return False
            
        socket.gethostbyname(host)
        with socket.create_connection((host, port), timeout=0.2):
            return True
    except Exception:
        return False

@router.post("/smoke-test")
def trigger_e2e_smoke_test(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Triggers the E2E Smoke Test workflow execution in backend."""
    from scripts.run_e2e_smoke_test import run_smoke_test
    background_tasks.add_task(run_smoke_test)
    return {"message": "E2E Smoke Test triggered successfully in the background."}

@router.get("/health/liveness")
def get_liveness():
    """Liveness endpoint to verify the API gateway process is up."""
    return {"status": "alive", "timestamp": time.time()}


@router.get("/health/readiness")
def get_readiness(db: Session = Depends(get_db)):
    """Readiness check validating SQL Database, Redis, and Storage availability."""
    checks = {}
    
    # 1. DB
    try:
        db.execute(text("SELECT 1"))
        checks["database"] = "UP"
    except Exception:
        checks["database"] = "DOWN"

    # 2. Redis
    from core.config import settings
    if _is_service_reachable(settings.REDIS_URL, 6379):
        try:
            import redis
            url = urlparse(settings.REDIS_URL)
            r = redis.Redis(host=url.hostname or "localhost", port=url.port or 6379, db=0, socket_connect_timeout=1)
            r.ping()
            checks["redis"] = "UP"
        except Exception:
            checks["redis"] = "DOWN"
    else:
        checks["redis"] = "DOWN"

    # 3. MinIO
    try:
        from storage.s3 import storage_client
        if storage_client and storage_client.client and _is_service_reachable(settings.MINIO_ENDPOINT, 9000):
            storage_client.client.list_buckets()
            checks["minio"] = "UP"
        else:
            checks["minio"] = "DOWN"
    except Exception:
        checks["minio"] = "DOWN"

    overall_status = "ready" if all(v == "UP" for v in checks.values()) else "not_ready"
    
    return JSONResponse(
        status_code=200 if overall_status == "ready" else 503,
        content={"status": overall_status, "checks": checks}
    )


@router.get("/health/version")
def get_version():
    """Version metadata checker endpoint."""
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    return {
        "application_version": "1.0.0-rc1",
        "database_schema_version": "981b89eaf0e1"
    }


@router.get("/health/dependencies")
def get_dependencies_health(db: Session = Depends(get_db)):
    """Check connections timing latencies in milliseconds."""
    latencies = {}
    
    # Database latency
    t0 = time.time()
    try:
        db.execute(text("SELECT 1"))
        latencies["database_ms"] = round((time.time() - t0) * 1000, 2)
    except Exception:
        latencies["database_ms"] = -1.0

    # Redis latency
    t0 = time.time()
    from core.config import settings
    if _is_service_reachable(settings.REDIS_URL, 6379):
        try:
            import redis
            url = urlparse(settings.REDIS_URL)
            r = redis.Redis(host=url.hostname or "localhost", port=url.port or 6379, db=0, socket_connect_timeout=1)
            r.ping()
            latencies["redis_ms"] = round((time.time() - t0) * 1000, 2)
        except Exception:
            latencies["redis_ms"] = -1.0
    else:
        latencies["redis_ms"] = -1.0

    return {"latencies": latencies}


@router.get("/manifest")
def get_manifest():
    """Exposes the build manifest of this release candidate."""
    if os.path.exists(MANIFEST_PATH):
        with open(MANIFEST_PATH, "r") as f:
            return json.load(f)
    raise HTTPException(status_code=404, detail="Manifest file not found.")


@router.get("/download/{filename}")
def download_release_report(
    filename: str,
    current_user: User = Depends(get_current_user)
):
    """Serve any of the compiled release PDF or JSON reports."""
    safe_filename = os.path.basename(filename)
    report_path = os.path.join(REPORTS_DIR, safe_filename)
    
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail=f"Report file '{safe_filename}' not found.")
        
    return FileResponse(report_path, filename=safe_filename)
