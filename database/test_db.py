import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_config import get_db_credentials, get_db_connection

def test():
    print("Resolved credentials:")
    host, port, user, password, name = get_db_credentials()
    print(f"  Host: {host}")
    print(f"  Port: {port}")
    print(f"  User: {user}")
    print(f"  Password: {'*' * len(password)}")
    print(f"  Database Name: {name}")

    print("\nAttempting connection...")
    try:
        conn = get_db_connection(autocommit=True)
        cursor = conn.cursor()
        print("Successfully connected!")
        
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"\nTables found ({len(tables)}):")
        for t in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {t}")
            cnt = cursor.fetchone()[0]
            print(f"  - {t:30}: {cnt} records")
            
        conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test()
