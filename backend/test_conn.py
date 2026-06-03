import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import get_settings
from sqlalchemy import create_engine, text

def test_connection():
    settings = get_settings()
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db_conn_test.txt")
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write(f"Settings DATABASE_URL: {settings.DATABASE_URL}\n")
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                out.write("Successfully connected to database!\n")
                
                # Check tables
                tables = [
                    "customers",
                    "users",
                    "orders",
                    "milestones",
                    "media_files",
                    "documents",
                    "notifications",
                    "audit_logs",
                    "login_sessions"
                ]
                
                for t in tables:
                    try:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {t}"))
                        count = result.scalar()
                        out.write(f"Table {t:20}: {count} records\n")
                    except Exception as err:
                        out.write(f"Error querying table {t}: {err}\n")
                        
            out.write("Database connection test finished successfully.\n")
        except Exception as e:
            out.write(f"Connection error: {e}\n")

if __name__ == "__main__":
    test_connection()
