
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT p.brand, c.name, COUNT(p.id) FROM products p JOIN colors c ON p.id=c.product_id GROUP BY p.brand, c.name HAVING COUNT(p.id) > 1")
for r in cur.fetchall(): print(r)

