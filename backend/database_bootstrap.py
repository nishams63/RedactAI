import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from database.session import engine, Base
from core.config import settings
import models  # noqa: F401

# Tables managed by Alembic migrations
ALEMBIC_TABLES = {
    "performance_benchmarks",
    "performance_profiles",
    "queue_metrics",
    "audit_logs",
    "login_attempts",
    "security_alerts",
    "password_histories",
    "user_sessions",
    "benchmark_questions",
    "benchmark_runs",
    "prompt_registry",
}

def bootstrap():
    mode = settings.DEPLOYMENT_MODE
    print(f"Bootstrapping database in [{mode}] mode...")

    # Drop tables logic for clean non-production bootstrap
    if mode != "production":
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        if existing_tables:
            print(f"Found {len(existing_tables)} existing tables. Cleaning up...")
            Base.metadata.drop_all(bind=engine)
            with engine.connect() as conn:
                conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
                conn.commit()
            print("Cleanup complete.")

    # For production and development, create base schema and run migrations
    if mode in ("production", "development"):
        print("Creating base tables not managed by Alembic...")
        tables_to_create = [
            table for name, table in Base.metadata.tables.items()
            if name not in ALEMBIC_TABLES
        ]
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
        
        print("Running Alembic head migrations...")
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations applied successfully.")
        return

    # For single and huggingface, create all tables directly and stamp head
    print("Creating all tables from models...")
    Base.metadata.create_all(bind=engine)
    print("All tables created successfully.")

    # Stamp Alembic to head
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Alembic stamped to head revision. Bootstrap complete!")

if __name__ == "__main__":
    bootstrap()
