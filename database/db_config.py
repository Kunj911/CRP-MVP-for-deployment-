"""
database/db_config.py

Shared database connection settings resolver.
Avoids duplicating DB password fallbacks and environment parsing logic.
Supports both MySQL (pymysql) and PostgreSQL (psycopg2) drivers dynamically.
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
    db_port = int(os.environ.get("DB_PORT") or env_vars.get("DB_PORT", 5432))
    db_user = os.environ.get("DB_USER") or env_vars.get("DB_USER", "root")
    db_pass = os.environ.get("DB_PASSWORD") or env_vars.get("DB_PASSWORD", "")
    db_name = os.environ.get("DB_NAME") or env_vars.get("DB_NAME", "live_trace_dashboard")
    
    db_url = os.environ.get("DATABASE_URL") or env_vars.get("DATABASE_URL", "")
    if db_url:
        drivers = ["mysql+pymysql://", "postgresql+psycopg2://", "postgresql://", "postgres://"]
        for driver in drivers:
            if driver in db_url:
                try:
                    without_driver = db_url.split(driver)[1]
                    user_pass, host_port_db = without_driver.split("@")
                    db_user = user_pass.split(":")[0]
                    db_pass = user_pass.split(":")[1] if ":" in user_pass else ""
                    
                    if "/" in host_port_db:
                        host_port, dbname_query = host_port_db.split("/", 1)
                        db_name = dbname_query.split("?")[0]
                    else:
                        host_port = host_port_db
                        db_name = "live_trace_dashboard"
                        
                    if ":" in host_port:
                        db_host, port_str = host_port.split(":")
                        db_port = int(port_str)
                    else:
                        db_host = host_port
                        db_port = 5432 if "post" in driver else 3306
                    break
                except Exception:
                    pass
            
    return db_host, db_port, db_user, db_pass, db_name

def get_db_connection(autocommit=False):
    """Establish and return a database connection (psycopg2 for PostgreSQL, pymysql for MySQL)"""
    db_host, db_port, db_user, db_pass, db_name = get_db_credentials()
    
    env_vars = parse_env()
    db_url = os.environ.get("DATABASE_URL") or env_vars.get("DATABASE_URL", "")
    
    is_postgres = "postgres" in db_url or "postgresql" in db_url or db_port == 5432
    
    if is_postgres:
        import psycopg2
        conn = psycopg2.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            dbname=db_name
        )
        if autocommit:
            conn.autocommit = True
        return conn
    else:
        import pymysql
        return pymysql.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_pass,
            database=db_name,
            autocommit=autocommit
        )
