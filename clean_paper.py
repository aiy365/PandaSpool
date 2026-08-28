
import sqlite3
import re
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("SELECT id, product_id, name, unopened, opened FROM colors")
all_colors = cur.fetchall()

for cid, pid, name, unop, op in all_colors:
    clean_name = re.sub(r"\s*\([^)]*盘\)\s*", "", name)
    clean_name = clean_name.strip()
    
    if clean_name != name:
        cur.execute("SELECT id FROM colors WHERE product_id=? AND name=?", (pid, clean_name))
        tc = cur.fetchone()
        if tc:
            tc_id = tc[0]
            cur.execute("UPDATE colors SET unopened = unopened + ?, opened = opened + ? WHERE id=?", (unop, op, tc_id))
            cur.execute("UPDATE stock_ins SET color_id=? WHERE color_id=?", (tc_id, cid))
            cur.execute("DELETE FROM colors WHERE id=?", (cid,))
        else:
            cur.execute("UPDATE colors SET name=? WHERE id=?", (clean_name, cid))

conn.commit()
print("Cleaned paper spools.")

