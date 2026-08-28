
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
for row in conn.execute("SELECT id, brand, product_line, material FROM products"):
    print(row)

