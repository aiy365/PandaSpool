
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, brand, created_at FROM products ORDER BY created_at DESC LIMIT 10")
print("Recent products:")
for r in cur.fetchall(): print(r)

cur.execute("SELECT id, created_at FROM stock_ins ORDER BY created_at DESC LIMIT 10")
print("Recent stock_ins:")
for r in cur.fetchall(): print(r)

