
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, name, color_family, unopened, opened, notes FROM colors WHERE unopened IS NULL OR opened IS NULL OR name IS NULL OR color_family IS NULL OR notes IS NULL")
print("Null colors:", cur.fetchall())
cur.execute("SELECT id, brand, product_line, material, notes FROM products WHERE brand IS NULL OR product_line IS NULL OR material IS NULL OR notes IS NULL")
print("Null products:", cur.fetchall())

