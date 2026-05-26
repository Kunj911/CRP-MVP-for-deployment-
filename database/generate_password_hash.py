"""
generate_password_hash.py

Generates a real bcrypt hash for a test password and patches
the dummy data SQL file so all users can actually log in.

Usage:
    python generate_password_hash.py

This will:
1. Print the bcrypt hash for the test password.
2. Replace all 'hashed_password_123' placeholders in 'dummy data.sql'
   with the real hash.

Default test password: Admin@123
"""

import re
from pathlib import Path
from passlib.context import CryptContext

# ── Config ────────────────────────────────────────────────────────────────────
TEST_PASSWORD = "Admin@123"          # Password you will use to log in
SQL_FILE     = Path(__file__).parent / "dummy data.sql"
PLACEHOLDER  = "hashed_password_123"

# ── Generate hash ─────────────────────────────────────────────────────────────
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
real_hash   = pwd_context.hash(TEST_PASSWORD)

print(f"\n✅  Test password : {TEST_PASSWORD}")
print(f"✅  Bcrypt hash   : {real_hash}\n")

# ── Patch the SQL file ────────────────────────────────────────────────────────
if SQL_FILE.exists():
    content     = SQL_FILE.read_text(encoding="utf-8")
    count       = content.count(PLACEHOLDER)

    if count == 0:
        print("ℹ️  No placeholder found — SQL file is already patched or uses a different placeholder.")
    else:
        patched = content.replace(PLACEHOLDER, real_hash)
        SQL_FILE.write_text(patched, encoding="utf-8")
        print(f"✅  Replaced {count} occurrence(s) of '{PLACEHOLDER}' in '{SQL_FILE.name}'.")
        print("    You can now import the patched SQL file into your database.")
else:
    print(f"⚠️  SQL file not found at: {SQL_FILE}")
    print(f"    Copy the hash above and manually replace 'hashed_password_123' in your SQL file.")

print()
print("── Login credentials for all seeded users ──────────────────────────")
print(f"   Password : {TEST_PASSWORD}")
print("   Email    : (use any email from the SQL file, e.g. admin@livetrace.com)")
print("────────────────────────────────────────────────────────────────────\n")
