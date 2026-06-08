"""
database/db_config.py

Shared database connection settings resolver.
Avoids duplicating DB password fallbacks and environment parsing logic.
Supports MySQL connections through pymysql.
"""

import os

def parse_env():
    """Parse DB credentials from backend/.env file"""
    env_vars = {}
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.abspath(os.path.join(current_dir, "..", "backend", ".env"))
    if not os.path.exists(env_path):
        env_path = os.path.abspath(os.path.join(current_dir, "backend", ".env"))
    
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    parts = line.split("=", 1)
                    key = parts[0].strip()
                    val = parts[1].strip()
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    elif val.startswith("'") and val.endswith("'"):
                        val = val[1:-1]
                    env_vars[key] = val
    return env_vars

def get_db_credentials():
    """Get DB credentials from environment variables or backend/.env fallback"""
    env_vars = parse_env()
    
    db_host = os.environ.get("DB_HOST") or env_vars.get("DB_HOST", "localhost")
    db_port = int(os.environ.get("DB_PORT") or env_vars.get("DB_PORT", 3306))
    db_user = os.environ.get("DB_USER") or env_vars.get("DB_USER", "root")
    db_pass = os.environ.get("DB_PASSWORD") or env_vars.get("DB_PASSWORD", "2104")
    db_name = os.environ.get("DB_NAME") or env_vars.get("DB_NAME", "live_trace_dashboard")
            
    return db_host, db_port, db_user, db_pass, db_name

def get_db_connection(autocommit=False):
    """Establish and return a MySQL database connection."""
    db_host, db_port, db_user, db_pass, db_name = get_db_credentials()

    import pymysql
    return pymysql.connect(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_pass,
        database=db_name,
        autocommit=autocommit
    )
