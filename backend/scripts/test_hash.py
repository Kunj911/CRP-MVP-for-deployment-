import bcrypt

stored_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/HS.V/Ym"
passwords = ["Admin@123", "admin123", "admin", "Admin123", "Admin@123 ", " Admin@123", "admin@123", "admin@live-trace.com", "admin@livetrace.com"]

with open("hash_test_results.txt", "w") as f:
    for pw in passwords:
        pw_bytes = pw.encode("utf-8")
        hash_bytes = stored_hash.encode("utf-8")
        try:
            match = bcrypt.checkpw(pw_bytes, hash_bytes)
            f.write(f"Password '{pw}' matches: {match}\n")
        except Exception as e:
            f.write(f"Password '{pw}' error: {e}\n")
