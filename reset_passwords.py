import psycopg2
import bcrypt

conn = psycopg2.connect(
    dbname="cinegraph",
    user="lalithadityareddy",
    host="localhost"
)

cur = conn.cursor()

DEFAULT_PASSWORD = "password123"

hashed = bcrypt.hashpw(
    DEFAULT_PASSWORD.encode(),
    bcrypt.gensalt()
).decode()

cur.execute("""
    UPDATE users
    SET password_hash = %s
""", (hashed,))

conn.commit()
cur.close()
conn.close()

print("✅ All user passwords reset to: password123")
