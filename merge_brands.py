
import sqlite3

conn = sqlite3.connect("data/app.sqlite3")
cur = conn.cursor()

# Get existing Polymaker (ID: 2d2ac091692cf7ac51a2a0f263f5c464)
# And the new POLYMAKER Panchroma (ID is different)
cur.execute("SELECT id FROM products WHERE brand=\"POLYMAKER\" AND product_line=\"Panchroma\"")
new_panchroma = cur.fetchone()
cur.execute("SELECT id FROM products WHERE brand=\"Polymaker\" AND product_line=\"Panchroma\"")
old_panchroma = cur.fetchone()

if new_panchroma and old_panchroma:
    cur.execute("UPDATE colors SET product_id=? WHERE product_id=?", (old_panchroma[0], new_panchroma[0]))
    cur.execute("DELETE FROM products WHERE id=?", (new_panchroma[0],))

# Also fix the general brand name
cur.execute("UPDATE products SET brand=\"Polymaker\" WHERE brand=\"POLYMAKER\"")

conn.commit()
print("Merged!")

