
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("DELETE FROM products WHERE brand=\"\"")
cur.execute("SELECT product_id, name, COUNT(id) FROM colors GROUP BY product_id, name HAVING COUNT(id) > 1")
dups = cur.fetchall()
print("Duplicate colors in same product:", dups)
conn.commit()

