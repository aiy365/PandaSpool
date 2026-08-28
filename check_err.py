
import sqlite3
conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id FROM products ORDER BY created_at DESC")
for row in cur.fetchall():
    p_id = row[0]
    try:
        cur.execute("SELECT id,product_id,name,color_family,unopened,opened,notes FROM colors WHERE product_id=?", (p_id,))
        cols = cur.fetchall()
        for col in cols:
            pass # pretend we process it
    except Exception as e:
        print(f"Error on product {p_id}: {e}")
print("Done checking colors")

