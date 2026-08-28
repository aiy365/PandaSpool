
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT p.id, p.brand, p.product_line, p.material, c.name, c.unopened, c.opened FROM products p JOIN colors c ON p.id=c.product_id WHERE p.brand=\"彩多屋\"")
for r in cur.fetchall(): print(r)

