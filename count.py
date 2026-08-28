
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM products")
print("Total products:", cur.fetchone()[0])

