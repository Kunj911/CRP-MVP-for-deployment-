import bcrypt
password = "Admin@123"
# Using rounds=12 to match standard strength
salt = bcrypt.gensalt(rounds=12)
hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
with open("new_admin_hash.txt", "w") as f:
    f.write(hashed.decode('utf-8'))
print("Done!")
