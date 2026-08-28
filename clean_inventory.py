
import sqlite3

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# 1. Merge remaining products that I missed
merges = [
    ("遇果", "通用", "PLIG", "遇果", "", "PETG"),
    ("遇果", "遇果2号", "PLA", "遇果", "", "PLA"), # Wait, does "遇果 | | PLA" exist? Let`s check first.
]

for sb, sl, sm, tb, tl, tm in merges:
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (sb, sl, sm))
    source = cur.fetchone()
    if not source: continue
    source_id = source[0]
    
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (tb, tl, tm))
    target = cur.fetchone()
    
    if target:
        target_id = target[0]
        # Move colors
        cur.execute("SELECT id, name, unopened, opened FROM colors WHERE product_id=?", (source_id,))
        for sc_id, sc_name, sc_unopened, sc_opened in cur.fetchall():
            cur.execute("SELECT id FROM colors WHERE product_id=? AND name=?", (target_id, sc_name))
            tc = cur.fetchone()
            if tc:
                tc_id = tc[0]
                cur.execute("UPDATE colors SET unopened = unopened + ?, opened = opened + ? WHERE id=?", (sc_unopened, sc_opened, tc_id))
                cur.execute("UPDATE stock_ins SET color_id=? WHERE color_id=?", (tc_id, sc_id))
                cur.execute("DELETE FROM colors WHERE id=?", (sc_id,))
            else:
                cur.execute("UPDATE colors SET product_id=? WHERE id=?", (target_id, sc_id))
        cur.execute("DELETE FROM products WHERE id=?", (source_id,))
    else:
        # If target doesn`t exist, just rename the source product to target
        cur.execute("UPDATE products SET product_line=?, material=? WHERE id=?", (tl, tm, source_id))

# 2. Clean up Color names: strip "(无线盘)", "(无料盘)", "(有料盘)", etc.
import re
cur.execute("SELECT id, product_id, name, unopened, opened FROM colors")
all_colors = cur.fetchall()

for cid, pid, name, unop, op in all_colors:
    # Regex to remove anything in parentheses that mentions 线盘 or 料盘
    clean_name = re.sub(r"\s*\(无?[线料]盘\)\s*", "", name)
    clean_name = clean_name.strip()
    
    if clean_name != name:
        # Check if the clean_name already exists in the same product
        cur.execute("SELECT id FROM colors WHERE product_id=? AND name=?", (pid, clean_name))
        tc = cur.fetchone()
        if tc:
            tc_id = tc[0]
            # Merge into the existing clean color
            cur.execute("UPDATE colors SET unopened = unopened + ?, opened = opened + ? WHERE id=?", (unop, op, tc_id))
            cur.execute("UPDATE stock_ins SET color_id=? WHERE color_id=?", (tc_id, cid))
            cur.execute("DELETE FROM colors WHERE id=?", (cid,))
        else:
            # Just rename it
            cur.execute("UPDATE colors SET name=? WHERE id=?", (clean_name, cid))

conn.commit()
print("Inventory cleaned!")

