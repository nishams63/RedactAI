from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from core.config import settings

# Engine configuration
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    # Connect args are not needed for psycopg2
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
