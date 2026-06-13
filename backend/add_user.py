"""
Add a new user to the CRP database.

Usage via Railway:
    railway run "python add_user.py --name 'Jane Doe' --email jane@co.com --role QA --password 'Temp@1234'"

Usage with direct DB:
    python add_user.py --db-host ... --db-pass ... --name "Jane" --email j@co.com --role QA --password "x"

Roles: SUPER_ADMIN, ADMIN, WAREHOUSE, QA, DOCUMENTATION, CUSTOMER
"""
import argparse
import os
import sys

try:
    import bcrypt
except ImportError:
    os.system(f"{sys.executable} -m pip install bcrypt pymysql python-dotenv")
    import bcrypt

import pymysql
from dotenv import load_dotenv

load_dotenv()


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Add a new user to CRP")
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--role", required=True, choices=[
        "SUPER_ADMIN", "ADMIN", "WAREHOUSE", "QA", "DOCUMENTATION", "CUSTOMER"
    ])
    parser.add_argument("--password", required=True)
    parser.add_argument("--phone", default="")
    parser.add_argument("--db-host", default=os.getenv("DB_HOST", "localhost"))
    parser.add_argument("--db-port", type=int, default=int(os.getenv("DB_PORT", 3306)))
    parser.add_argument("--db-user", default=os.getenv("DB_USER", "root"))
    parser.add_argument("--db-pass", default=os.getenv("DB_PASSWORD", ""))
    parser.add_argument("--db-name", default=os.getenv("DB_NAME", "live_trace_dashboard"))
    args = parser.parse_args()

    conn = pymysql.connect(
        host=args.db_host, port=args.db_port, user=args.db_user,
        password=args.db_pass, database=args.db_name,
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (args.email,))
            if cur.fetchone():
                print(f"ERROR: Email '{args.email}' already exists.")
                return

            pw_hash = hash_password(args.password)
            cur.execute(
                """INSERT INTO users (full_name, email, phone, password_hash, role, is_active)
                   VALUES (%s, %s, %s, %s, %s, TRUE)""",
                (args.name, args.email, args.phone, pw_hash, args.role.upper()),
            )
            conn.commit()
            print(f"✅ User created: {args.name} <{args.email}> role={args.role}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
