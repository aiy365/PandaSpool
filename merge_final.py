
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

merges = [
    ("三绿", "Lite", "PLA", "三绿", "Lite", "PLA Lite"),
    ("三绿", "Matte", "PLA", "三绿", "Matte", "PLA Matte"),
    ("三绿", "PLA+ 2.0", "PLA", "三绿", "", "PLA+2.0"),
    ("大简", "HF", "PLIG/HF", "大简", "HF", "PETG HF"),
    ("必趣", "PLA GO", "PLA", "必趣", "PLA GO", "PLA GO"),
    ("拓竹", "Lite", "PLA", "拓竹", "Lite", "PLA Lite"),
    ("拓竹", "Matte", "PLA", "拓竹", "Matte", "PLA Matte"),
]

for sb, sl, sm, tb, tl, tm in merges:
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (sb, sl, sm))
    source = cur.fetchone()
    cur.execute("SELECT id FROM products WHERE brand=? AND product_line=? AND material=?", (tb, tl, tm))
    target = cur.fetchone()
    
    if source and target:
        source_id = source[0]
        target_id = target[0]
        print(f"Merging {sb} {sl} {sm} into {tb} {tl} {tm}")
        
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

# Let`s also check if they want 遇果 通用 PLIG merged into 遇果 PETG ?
# User`s screenshot has `遇果 (PLIG)`. The DB has `遇果 | | PETG`.
# Let`s merge `遇果 | | PETG` to `遇果 | | PLIG` ? No, the DB actually has PETG.
# Wait, let`s check 遇果.
cur.execute("SELECT id, product_line, material FROM products WHERE brand=\"遇果\"")
print("Yuguo:", cur.fetchall())

conn.commit()

