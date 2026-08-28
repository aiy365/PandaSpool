
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# Merge duplicate colors inside the same product
cur.execute("SELECT product_id, name FROM colors GROUP BY product_id, name HAVING COUNT(id) > 1")
dups = cur.fetchall()

for pid, name in dups:
    cur.execute("SELECT id, unopened, opened FROM colors WHERE product_id=? AND name=?", (pid, name))
    records = cur.fetchall()
    
    keep_id = records[0][0]
    total_unop = 0
    total_op = 0
    
    for r in records[1:]:
        del_id = r[0]
        total_unop += r[1]
        total_op += r[2]
        # Move stock_ins to keep_id
        cur.execute("UPDATE stock_ins SET color_id=? WHERE color_id=?", (keep_id, del_id))
        # Delete duplicate color
        cur.execute("DELETE FROM colors WHERE id=?", (del_id,))
    
    # Add accumulated totals to keep_id
    cur.execute("UPDATE colors SET unopened = unopened + ?, opened = opened + ? WHERE id=?", (total_unop, total_op, keep_id))

conn.commit()
print("Fixed duplicate colors.")

