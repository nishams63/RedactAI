import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import inspect, text
from database.session import engine, Base
import models  # noqa: F401

def bootstrap():
    """Drop any leftover tables from failed deploys, create all fresh, and stamp Alembic."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    if existing_tables:
        print(f"Found {len(existing_tables)} existing tables: {existing_tables}")
        # Check if alembic_version exists and is already at head
        if "alembic_version" in existing_tables:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version"))
                versions = [row[0] for row in result]
                if versions:
                    print(f"Alembic already stamped at: {versions}. Skipping bootstrap.")
                    return
        
        # Tables exist but no alembic stamp — leftover from failed deploy
        print("Dropping leftover tables from failed deploys...")
        Base.metadata.drop_all(bind=engine)
        # Also drop alembic_version if it exists
        with engine.connect() as conn:
            conn.execute(text("DROP TABLE IF EXISTS alembic_version"))
            conn.commit()
        print("All leftover tables dropped.")
    
    print("Creating all database tables from SQLAlchemy models...")
    Base.metadata.create_all(bind=engine)
    print("All database tables created successfully!")

    # Stamp Alembic to head so it knows all migrations are "applied"
    from alembic.config import Config
    from alembic import command
    alembic_cfg = Config("alembic.ini")
    command.stamp(alembic_cfg, "head")
    print("Alembic stamped to head revision. Bootstrap complete!")

if __name__ == "__main__":
    bootstrap()
