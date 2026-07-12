import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.session import engine, Base
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
    # If explicitly requested, drop all tables to start fresh (useful for resetting corrupted schemas)
    if os.getenv("DROP_TABLES_ON_START", "false").lower() == "true":
        print("DROP_TABLES_ON_START is enabled. Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("All tables dropped successfully.")

    print("Bootstrapping database: identifying base tables to create...")
    
    # Filter Base.metadata to ONLY create base tables not managed by Alembic
    tables_to_create = [
        table for name, table in Base.metadata.tables.items()
        if name not in ALEMBIC_TABLES
    ]
    
    print(f"Creating {len(tables_to_create)} base tables...")
    Base.metadata.create_all(bind=engine, tables=tables_to_create)
    print("Database base tables bootstrapped successfully!")

if __name__ == "__main__":
    bootstrap()
