
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT DISTINCT p.id, p.brand, p.product_line FROM products p JOIN colors c ON p.id = c.product_id WHERE c.unopened > 0 OR c.opened > 0")
rows = cur.fetchall()
print(f"Total products on shelf: {len(rows)}")
for r in rows:
    print(r)

