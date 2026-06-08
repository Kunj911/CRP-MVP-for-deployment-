"""
scripts/diagnose_login.py

Diagnose login issues by checking:
  1. .env file exists and DB_NAME is correct
  2. Database connectivity
  3. The admin user row exists in the DB
  4. The password hash in the DB matches 'Admin@123'
  5. The users table has all required columns (mfa_enabled, totp_secret)

Usage (from backend/ directory):
    python scripts/diagnose_login.py
"""

import os
import sys

# Ensure the backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

def main():
    print("=" * 60)
    print("  LIVE-TRACE LOGIN DIAGNOSTICS")
    print("=" * 60)
    issues_found = []

    # ── 1. Check .env file ────────────────────────────────────────
    print("\n[1] Checking .env file...")
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(backend_dir, ".env")
    if os.path.exists(env_path):
        print(f"  {PASS} .env file found at: {env_path}")
        with open(env_path, "r") as f:
            env_content = f.read()
        # Check DB_NAME
        if "DB_NAME" in env_content:
            for line in env_content.splitlines():
                if line.strip().startswith("DB_NAME"):
                    val = line.split("=", 1)[1].strip()
                    print(f"  {PASS} DB_NAME = {val}")
                    if val != "live_trace_dashboard":
                        issues_found.append(
                            f"DB_NAME is '{val}' but SQL schema uses 'live_trace_dashboard'"
                        )
                        print(f"  {FAIL} Expected 'live_trace_dashboard', got '{val}'")
        else:
            print(f"  {WARN} DB_NAME not set in .env — default is 'live_trace_dashboard'")
            issues_found.append(
                "DB_NAME not in .env — backend defaults to 'live_trace_dashboard'"
            )
    else:
        print(f"  {FAIL} .env file NOT FOUND!")
        print(f"     Backend will use defaults: DB_NAME='live_trace_dashboard', DB_PASSWORD='2104'")
        issues_found.append(
            "No .env file — backend uses built-in MySQL defaults for local development"
        )

    # ── 2. Try loading settings ───────────────────────────────────
    print("\n[2] Loading app settings...")
    try:
        from app.config.settings import get_settings
        settings = get_settings()
        print(f"  {PASS} Settings loaded successfully")
        print(f"     DB_HOST:     {settings.DB_HOST}")
        print(f"     DB_PORT:     {settings.DB_PORT}")
        print(f"     DB_NAME:     {settings.DB_NAME}")
        print(f"     DB_USER:     {settings.DB_USER}")
        print(f"     DB_PASSWORD: {'*' * len(settings.DB_PASSWORD) if settings.DB_PASSWORD else '(empty)'}")
        print(f"     DATABASE_URL: {settings.DATABASE_URL.replace(settings.DB_PASSWORD, '***') if settings.DB_PASSWORD else settings.DATABASE_URL}")
    except Exception as e:
        print(f"  {FAIL} Could not load settings: {e}")
        issues_found.append(f"Settings load error: {e}")
        print("\n⛔ Cannot continue without settings. Fix .env first.")
        _print_summary(issues_found)
        return

    # ── 3. Check DB connectivity ──────────────────────────────────
    print("\n[3] Checking database connectivity...")
    try:
        from app.database.connection import check_db_connection
        if check_db_connection():
            print(f"  {PASS} Database is reachable")
        else:
            print(f"  {FAIL} Database is NOT reachable")
            issues_found.append("Cannot connect to the database — check DB_HOST, DB_PORT, DB_USER, DB_PASSWORD")
            _print_summary(issues_found)
            return
    except Exception as e:
        print(f"  {FAIL} Database connection error: {e}")
        issues_found.append(f"DB connection error: {e}")
        _print_summary(issues_found)
        return

    # ── 4. Check users table columns ──────────────────────────────
    print("\n[4] Checking users table structure...")
    try:
        from sqlalchemy import text, inspect
        from app.database.connection import engine
        inspector = inspect(engine)
        columns = {col["name"] for col in inspector.get_columns("users")}
        print(f"  Columns found: {sorted(columns)}")

        required = {"user_id", "full_name", "email", "password_hash", "role", "is_active"}
        mfa_cols = {"mfa_enabled", "totp_secret"}

        missing_required = required - columns
        missing_mfa = mfa_cols - columns

        if missing_required:
            print(f"  {FAIL} Missing required columns: {missing_required}")
            issues_found.append(f"Missing required columns: {missing_required}")
        else:
            print(f"  {PASS} All required columns present")

        if missing_mfa:
            print(f"  {WARN} Missing MFA columns: {missing_mfa}")
            print(f"     The User model expects these — SQLAlchemy will crash on query!")
            issues_found.append(
                f"Missing MFA columns in users table: {missing_mfa}. "
                f"Run: ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT FALSE, "
                f"ADD COLUMN totp_secret VARCHAR(255) NULL;"
            )
        else:
            print(f"  {PASS} MFA columns present")
    except Exception as e:
        print(f"  {FAIL} Could not inspect users table: {e}")
        issues_found.append(f"Table inspection error: {e}")

    # ── 5. Check admin user exists ────────────────────────────────
    print("\n[5] Checking admin user in database...")
    try:
        from sqlalchemy import text
        from app.database.connection import engine
        with engine.connect() as conn:
            result = conn.execute(
                text("SELECT user_id, email, password_hash, role, is_active FROM users WHERE email = :email"),
                {"email": "admin@livetrace.com"},
            )
            row = result.fetchone()
            if row:
                user_id, email, pw_hash, role, is_active = row
                print(f"  {PASS} Admin user found:")
                print(f"     user_id:       {user_id}")
                print(f"     email:         {email}")
                print(f"     role:          {role}")
                print(f"     is_active:     {is_active}")
                print(f"     password_hash: {pw_hash[:30]}...")

                if not is_active:
                    print(f"  {FAIL} Account is DEACTIVATED — login will be rejected!")
                    issues_found.append("Admin account is_active = FALSE")

                # ── 6. Verify password hash ───────────────────────
                print("\n[6] Verifying password hash matches 'Admin@123'...")
                from app.core.security import verify_password
                if verify_password("Admin@123", pw_hash):
                    print(f"  {PASS} Password 'Admin@123' matches the stored hash!")
                else:
                    print(f"  {FAIL} Password 'Admin@123' does NOT match the hash!")
                    print(f"     Stored hash: {pw_hash}")
                    if pw_hash == "hashed_password_123":
                        print(f"     This is the PLACEHOLDER hash — the dummy data was imported before patching!")
                        issues_found.append(
                            "password_hash is the placeholder 'hashed_password_123', not a real bcrypt hash"
                        )
                    else:
                        issues_found.append(
                            f"password_hash does not match 'Admin@123'. Hash in DB: {pw_hash[:40]}..."
                        )
            else:
                print(f"  {FAIL} No user found with email 'admin@livetrace.com'!")
                issues_found.append("Admin user does not exist in the database")
    except Exception as e:
        print(f"  {FAIL} Error querying admin user: {e}")
        issues_found.append(f"Admin user query error: {e}")

    # ── 7. Check Redis (brute-force lockout) ──────────────────────
    print("\n[7] Checking Redis connectivity...")
    try:
        from app.core.redis_client import redis_client
        redis_client.ping()
        print(f"  {PASS} Redis is reachable")

        # Check if admin is currently locked out
        lockout_key = "failed_login:email:admin@livetrace.com"
        count = redis_client.get(lockout_key)
        if count:
            print(f"  {WARN} Failed login attempts for admin: {count}/5")
            if int(count) >= 5:
                print(f"  {FAIL} ADMIN IS LOCKED OUT! Too many failed attempts.")
                issues_found.append(
                    "Admin is locked out due to brute-force protection. "
                    "Wait 15 minutes or run: redis_client.delete('failed_login:email:admin@livetrace.com')"
                )
        else:
            print(f"  {PASS} No lockout entries for admin")
    except Exception as e:
        print(f"  {WARN} Redis not reachable: {e}")
        print(f"     Login still works but brute-force protection is disabled")

    _print_summary(issues_found)


def _print_summary(issues):
    print("\n" + "=" * 60)
    if not issues:
        print(f"  {PASS} ALL CHECKS PASSED — Login should work!")
        print("=" * 60)
    else:
        print(f"  {FAIL} FOUND {len(issues)} ISSUE(S):")
        print("=" * 60)
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()


if __name__ == "__main__":
    main()
