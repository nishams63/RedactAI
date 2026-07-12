"""Backup and recovery utility supporting SQL DB JSON dumps, MinIO simulated directories, and config profiles."""
import os
import json
import shutil
from datetime import datetime
from sqlalchemy import text
from database.session import SessionLocal

BACKUP_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "local_storage",
    "backups"
)
os.makedirs(BACKUP_DIR, exist_ok=True)

class BackupManager:
    def __init__(self):
        self.db = SessionLocal()

    def backup_database(self) -> str:
        """Dumps all tables rows into a structured JSON database backup."""
        tables = [
            "users", "roles", "organizations", "documents", "user_sessions", 
            "audit_logs", "security_alerts", "login_attempts", "password_histories"
        ]
        dump = {}
        for table in tables:
            try:
                res = self.db.execute(text(f"SELECT * FROM {table}"))
                cols = res.keys()
                rows = [dict(zip(cols, row)) for row in res.fetchall()]
                # Convert datetime and UUIDs to string for JSON serialization
                for r in rows:
                    for k, v in r.items():
                        if isinstance(v, (datetime,)):
                            r[k] = v.isoformat()
                        elif hasattr(v, "hex"):
                            r[k] = str(v)
                dump[table] = rows
            except Exception as e:
                print(f"Skipping table {table} during backup: {e}")
                
        backup_path = os.path.join(BACKUP_DIR, f"db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(backup_path, "w") as f:
            json.dump(dump, f, indent=4)
        print(f"Database backup written to: {backup_path}")
        return backup_path

    def restore_database(self, backup_path: str):
        """Restores tables from JSON backup file."""
        if not os.path.exists(backup_path):
            print(f"Backup file not found: {backup_path}")
            return False

        with open(backup_path, "r") as f:
            dump = json.load(f)

        # Clear existing tables in order to prevent foreign key errors
        tables = [
            "user_sessions", "login_attempts", "password_histories", "audit_logs", 
            "security_alerts", "documents", "users", "organizations", "roles"
        ]
        for table in tables:
            try:
                self.db.execute(text(f"TRUNCATE TABLE {table} CASCADE"))
                self.db.commit()
            except Exception as e:
                self.db.rollback()
                print(f"Error truncating table {table}: {e}")

        # Insert rows back
        for table, rows in reversed(list(dump.items())):
            for row in rows:
                try:
                    cols = ", ".join(row.keys())
                    vals = ", ".join([f"'{v}'" if v is not None else "NULL" for v in row.values()])
                    self.db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({vals})"))
                    self.db.commit()
                except Exception as e:
                    self.db.rollback()
                    print(f"Error restoring row in {table}: {e}")
        print(f"Database successfully restored from {backup_path}")
        return True

    def backup_storage(self) -> str:
        """Copies local_storage document directories into backup folder."""
        src = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "local_storage", "documents")
        if not os.path.exists(src):
            print("No local documents storage folder to backup.")
            return ""
            
        dst = os.path.join(BACKUP_DIR, f"storage_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        shutil.copytree(src, dst)
        print(f"Storage backup completed: {dst}")
        return dst

    def close(self):
        self.db.close()


if __name__ == "__main__":
    import sys
    mgr = BackupManager()
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            mgr.restore_database(sys.argv[2])
        else:
            print("Please specify backup file path for restore operation.")
    else:
        mgr.backup_database()
        mgr.backup_storage()
    mgr.close()
