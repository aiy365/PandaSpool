
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, created_at FROM products WHERE created_at IS NULL")
print("Null created_at:", cur.fetchall())

