import sqlite3

conn = sqlite3.connect("data/universities.db")

cursor = conn.cursor()
cursor.execute("SELECT * FROM universities LIMIT 1")

rows = cursor.fetchall()

for r in rows:
    print(r)

conn.close()