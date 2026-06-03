import os
import sys

# Add database folder to python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "database"))
from db_config import get_db_connection

def verify():
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_output.txt")
    
    with open(output_file, "w", encoding="utf-8") as out:
        out.write("Database verification started...\n")
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
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
            
            out.write("=" * 60 + "\n")
            out.write("                DATABASE VALIDATION SUMMARY\n")
            out.write("=" * 60 + "\n")
            
            for t in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cursor.fetchone()[0]
                out.write(f"Table {t:20}: {cnt} records\n")
                
            out.write("=" * 60 + "\n")
            
            # Check users and roles
            out.write("\nPlatform Users & Roles:\n")
            cursor.execute("SELECT email, role, full_name FROM users")
            for email, role, name in cursor.fetchall():
                out.write(f"  - {name} ({email}) -> {role}\n")
                
            # Check some orders
            out.write("\nSample Orders:\n")
            cursor.execute("SELECT order_code, product_name, shipment_status FROM orders LIMIT 5")
            for code, prod, status in cursor.fetchall():
                out.write(f"  - {code}: {prod} | Status: {status}\n")
                
            conn.close()
            out.write("\nVerification successfully completed!\n")
            print("Verification successfully completed!")
        except Exception as e:
            out.write(f"\nError connecting or querying: {e}\n")
            print(f"Error connecting or querying: {e}")

if __name__ == "__main__":
    verify()
