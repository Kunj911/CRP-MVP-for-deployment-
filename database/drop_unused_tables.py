import os
import sys

# Add database folder to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_config import get_db_connection

def drop_tables():
    print("Connecting to database...")
    try:
        conn = get_db_connection(autocommit=True)
        cursor = conn.cursor()
        print("Connected successfully!")
        
        print("Dropping table 'qa_reports' if exists...")
        cursor.execute("DROP TABLE IF EXISTS qa_reports")
        print("✓ Table 'qa_reports' dropped.")
        
        print("Dropping table 'order_comments' if exists...")
        cursor.execute("DROP TABLE IF EXISTS order_comments")
        print("✓ Table 'order_comments' dropped.")
        
        conn.close()
        print("Done!")
    except Exception as e:
        print(f"Error dropping tables: {e}")

if __name__ == "__main__":
    drop_tables()
