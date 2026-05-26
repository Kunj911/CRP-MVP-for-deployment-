import pymysql
import bcrypt

password = "Admin@123"
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.strip().encode('utf-8'), salt).decode('utf-8')

print(f"Generated hash for '{password}': {hashed}")

try:
    conn = pymysql.connect(
        host="localhost",
        port=3306,
        user="root",
        password="kunj@2006",
        database="live_trace_dashboard"
    )
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE email = 'admin@livetrace.com'",
        (hashed,)
    )
    conn.commit()
    print("✓ Database successfully updated with the new password hash!")
    
    # Verify the update
    cursor.execute("SELECT password_hash FROM users WHERE email = 'admin@livetrace.com'")
    row = cursor.fetchone()
    db_hash = row[0]
    print(f"✓ Verified hash in DB: {db_hash}")
    
    # Verify verification logic matches
    match = bcrypt.checkpw(password.strip().encode('utf-8'), db_hash.encode('utf-8'))
    print(f"✓ Bcrypt checkpw verification result: {match}")
    
    conn.close()
except Exception as e:
    print("✗ Error updating database:", e)
