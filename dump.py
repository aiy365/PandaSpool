
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, brand, product_line, material, created_at FROM products ORDER BY brand, product_line, material")
for r in cur.fetchall(): print(r)

