import bcrypt
from app.database.connection import SessionLocal
from app.models.user import User

db = SessionLocal()
u = db.query(User).filter(User.email == "test@fittree.com").first()
print(f"Stored hash: {u.password_hash}")

try:
    result = bcrypt.checkpw(b"Fittree@123", u.password_hash.encode("utf-8"))
    print(f"Direct bcrypt verify: {result}")
except Exception as e:
    print(f"bcrypt error: {e}")

new_hash = bcrypt.hashpw(b"Fittree@123", bcrypt.gensalt()).decode("utf-8")
print(f"New hash: {new_hash}")

try:
    result = bcrypt.checkpw(b"Fittree@123", new_hash.encode("utf-8"))
    print(f"New hash verify: {result}")
except Exception as e:
    print(f"New hash verify error: {e}")

u.password_hash = new_hash
db.commit()
print("Password updated!")
db.close()
