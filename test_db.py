# test_db.py
import psycopg2

conn = psycopg2.connect(
    dbname="cinegraph",
    user="lalithadityareddy",
    password="",
    host="localhost"
)

print("Connected successfully")
conn.close()
