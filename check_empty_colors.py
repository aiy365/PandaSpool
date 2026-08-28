
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, product_id, name FROM colors WHERE unopened=0 AND opened=0 AND notes=\"\"")
for r in cur.fetchall(): print(r)

