
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT brand, product_line, COUNT(id) FROM products GROUP BY brand, product_line HAVING COUNT(id) > 1")
for r in cur.fetchall(): print(r)

