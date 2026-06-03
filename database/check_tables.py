import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_config import get_db_connection

def main():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [row[0] for row in cursor.fetchall()]
        
        output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "current_tables.txt")
        with open(output_file, "w") as f:
            f.write("Current tables in database:\n")
            for t in tables:
                f.write(f"- {t}\n")
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
