import os
import sys
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Add parent to path to import core config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def backup_database(output_dir: str = None) -> str:
    """
    Creates a pg_dump backup of the PostgreSQL database defined in settings.
    """
    if not output_dir:
        output_dir = os.path.join(str(Path(__file__).resolve().parent.parent), "backups")
    
    os.makedirs(output_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f"db_backup_{timestamp}.sql")
    backup_log = os.path.join(output_dir, f"db_backup_{timestamp}.log")
    
    db_url = settings.database_url
    
    # Handle async driver prefix in URL
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        
    parsed_url = urlparse(db_url)
    db_name = parsed_url.path.lstrip('/')
    user = parsed_url.username or "postgres"
    password = parsed_url.password
    host = parsed_url.hostname or "localhost"
    port = parsed_url.port or 5432
    
    logger.info(f"Starting database backup for {db_name} at {host}:{port}")
    
    env = os.environ.copy()
    if password:
        env["PGPASSWORD"] = password
        
    command = [
        "pg_dump",
        "-U", user,
        "-h", host,
        "-p", str(port),
        "-F", "c",
        "-f", backup_file,
        db_name
    ]
    
    try:
        process = subprocess.run(command, env=env, check=True, capture_output=True, text=True)
        logger.info(f"Database backup completed successfully. Saved to: {backup_file}")
        
        with open(backup_log, "w", encoding="utf-8") as f:
            f.write(f"Backup SUCCESS for database: {db_name}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"File: {backup_file}\n")
            
        return backup_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Database backup failed: {e.stderr}")
        with open(backup_log, "w", encoding="utf-8") as f:
            f.write(f"Backup FAILED for database: {db_name}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Error: {e.stderr}\n")
        raise
    except FileNotFoundError:
        logger.error("pg_dump command not found. Please ensure PostgreSQL client tools are installed and in PATH.")
        raise

if __name__ == "__main__":
    try:
        backup_database()
    except Exception as e:
        logger.error(f"Backup process encountered an error: {e}")
        sys.exit(1)
