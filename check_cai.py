
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, brand, product_line, material FROM products WHERE brand LIKE \"%彩多屋%\"")
for r in cur.fetchall(): print(r)
cur.execute("SELECT id, brand, product_line, material FROM products WHERE brand LIKE \"%Poly%\" AND material=\"PETG\"")
for r in cur.fetchall(): print(r)

