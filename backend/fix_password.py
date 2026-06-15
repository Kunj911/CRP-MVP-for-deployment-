from app.database.connection import SessionLocal
from app.models.user import User
from passlib.context import CryptContext

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()
u = db.query(User).filter(User.email == "test@fittree.com").first()
print(f"Stored hash: {u.password_hash[:40]}...")
print(f"Verify Fittree@123: {pwd.verify('Fittree@123', u.password_hash)}")

u.password_hash = pwd.hash("Fittree@123")
db.commit()
print(f"New hash: {u.password_hash[:40]}...")
print(f"Verify again: {pwd.verify('Fittree@123', u.password_hash)}")
db.close()
print("Done - password reset to Fittree@123")
