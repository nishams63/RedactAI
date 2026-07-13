"""RedactAI — FastAPI Application Entry Point."""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from core.middleware import setup_middleware
from api.v1.router import api_v1_router
from database.session import engine, Base, SessionLocal
from database.seed import seed_database
from storage.s3 import storage_client

# Import all models so Base.metadata is fully populated
import models  # noqa: F401

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("redactai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    # --- Startup ---
    import os
    import uuid
    # Auto-create all required local storage directories
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(backend_dir)
    
    # Create in base_dir (project root)
    for folder in ["uploads", "reports", "cache", "models", "local_storage"]:
        os.makedirs(os.path.join(base_dir, folder), exist_ok=True)
    os.makedirs(os.path.join(base_dir, "local_storage", "reports"), exist_ok=True)
    
    # Create in backend_dir (backend root) to align with storage_client paths
    for folder in ["uploads", "reports", "cache", "models", "local_storage"]:
        os.makedirs(os.path.join(backend_dir, folder), exist_ok=True)
    os.makedirs(os.path.join(backend_dir, "local_storage", "reports"), exist_ok=True)
    os.makedirs(os.path.join(backend_dir, "local_storage", "uploads"), exist_ok=True)

    # Proactively check write permissions on the local storage paths
    for test_dir in [
        os.path.join(backend_dir, "local_storage"),
        os.path.join(backend_dir, "local_storage", "uploads"),
        os.path.join(base_dir, "local_storage"),
    ]:
        try:
            test_file = os.path.join(test_dir, f".write_test_{uuid.uuid4()}")
            with open(test_file, "w") as f:
                f.write("write test")
            os.remove(test_file)
            logger.info(f"Directory write check PASSED: {test_dir}")
        except Exception as e:
            logger.error(f"Directory write check FAILED: {test_dir}. Error: {e}")


    from core.secrets_validator import validate_startup_secrets
    validate_startup_secrets()
    
    logger.info(f"Starting RedactAI API [{settings.ENVIRONMENT}]")

    # Create database tables (Alembic should be used in production)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified")

    # Seed default data
    db = SessionLocal()
    try:
        seed_database(db)
    finally:
        db.close()

    # Ensure MinIO bucket exists
    try:
        storage_client.ensure_bucket()
        logger.info(f"MinIO bucket '{settings.MINIO_BUCKET}' verified")
    except Exception as e:
        logger.warning(f"MinIO bucket setup failed (non-blocking): {e}")

    yield

    # --- Shutdown ---
    logger.info("Shutting down RedactAI API")


app = FastAPI(
    title="RedactAI API",
    description="AI-powered Legal Document Privacy & Compliance Platform — API Gateway",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Attach middleware
setup_middleware(app)

# Mount versioned API routes
app.include_router(api_v1_router)


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint for load balancers and monitoring."""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": "1.0.0",
    }


@app.get("/health/liveness", tags=["Health"])
def health_liveness():
    """Liveness endpoint to verify the API gateway process is up."""
    return {"status": "alive"}
