
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT brand, product_line, material FROM products ORDER BY brand, product_line, material")
for r in cur.fetchall(): print(r)

