
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT p.brand, p.product_line, c.name, c.unopened, c.opened FROM products p JOIN colors c ON p.id = c.product_id WHERE p.brand LIKE \"%余%\"")
for row in cur.fetchall():
    print(row)

