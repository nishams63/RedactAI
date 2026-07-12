import os
import sys

# Ensure backend directory is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.session import engine, Base
import models  # noqa: F401

def bootstrap():
    print("Bootstrapping database: creating base tables if missing...")
    Base.metadata.create_all(bind=engine)
    print("Database tables bootstrapped successfully!")

if __name__ == "__main__":
    bootstrap()
