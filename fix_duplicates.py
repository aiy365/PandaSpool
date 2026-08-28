
import sqlite3

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# 1. Merge Polymaker 高速PETG into Polymaker 通用
cur.execute("SELECT id FROM products WHERE brand=\"Polymaker\" AND product_line=\"通用\" AND material=\"PETG\"")
target_poly = cur.fetchone()
cur.execute("SELECT id FROM products WHERE brand=\"Polymaker\" AND product_line=\"高速PETG\" AND material=\"PETG\"")
source_poly = cur.fetchone()

if target_poly and source_poly:
    target_id = target_poly[0]
    source_id = source_poly[0]
    # Move colors
    cur.execute("UPDATE colors SET product_id=? WHERE product_id=?", (target_id, source_id))
    cur.execute("DELETE FROM products WHERE id=?", (source_id,))
    print("Merged Polymaker PETG")

# 2. Merge 彩多屋 Silk PLA into 彩多屋 Silk PLA Silk
cur.execute("SELECT id FROM products WHERE brand=\"彩多屋\" AND product_line=\"Silk\" AND material=\"PLA Silk\"")
target_cai = cur.fetchone()
cur.execute("SELECT id FROM products WHERE brand=\"彩多屋\" AND product_line=\"Silk\" AND material=\"PLA\"")
source_cai = cur.fetchone()

if target_cai and source_cai:
    target_id = target_cai[0]
    source_id = source_cai[0]
    # First, let`s see if they have overlapping colors
    cur.execute("SELECT id, name, unopened, opened FROM colors WHERE product_id=?", (source_id,))
    source_colors = cur.fetchall()
    
    for sc in source_colors:
        sc_id, sc_name, sc_unopened, sc_opened = sc
        cur.execute("SELECT id FROM colors WHERE product_id=? AND name=?", (target_id, sc_name))
        tc = cur.fetchone()
        if tc:
            tc_id = tc[0]
            # Add quantities to target
            cur.execute("UPDATE colors SET unopened = unopened + ?, opened = opened + ? WHERE id=?", (sc_unopened, sc_opened, tc_id))
            # Move stock_ins
            cur.execute("UPDATE stock_ins SET color_id=? WHERE color_id=?", (tc_id, sc_id))
            # Delete source color
            cur.execute("DELETE FROM colors WHERE id=?", (sc_id,))
        else:
            # Move color to target
            cur.execute("UPDATE colors SET product_id=? WHERE id=?", (target_id, sc_id))
    
    cur.execute("DELETE FROM products WHERE id=?", (source_id,))
    print("Merged 彩多屋 PLA")

conn.commit()

