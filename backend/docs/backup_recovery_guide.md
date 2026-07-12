# RedactAI Backup & Recovery Guide

This guide details platform backup and restore procedures for the database, local storage objects, and system configurations.

## 1. Database & Object Storage Backups
Dumping and backing up data uses the integrated `backup_recovery.py` script.

To execute a complete backup:
```bash
venv/Scripts/python scripts/backup_recovery.py
```
This command performs two actions:
1. Exports all relational table rows (users, audit logs, sessions, prompts) to a JSON dump file in `local_storage/backups/`.
2. Copies all files in the `local_storage/documents/` folder to a timestamped backup directory.

## 2. Restore Procedure
To restore the platform to a previously saved baseline configuration, run the script with the `restore` argument and the path to the backup file:

```bash
venv/Scripts/python scripts/backup_recovery.py restore local_storage/backups/db_backup_XXXXXXXX_XXXXXX.json
```
This script truncates existing relational tables in order (resolving foreign keys) and inserts the row objects from the backup JSON format.
