
import sqlite3
import pandas as pd
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# Get all my inserts
cur.execute("SELECT id, color_id, qty, unit_price FROM stock_ins WHERE created_at LIKE \"2026-08-24T17:41%\"")
my_inserts = cur.fetchall()

for sid, cid, qty, price in my_inserts:
    # Check if there was an earlier stock_in for this color
    cur.execute("SELECT id, qty FROM stock_ins WHERE color_id=? AND id != ? ORDER BY created_at ASC", (cid, sid))
    earlier = cur.fetchall()
    
    if earlier:
        # User already had it! I should delete mine, subtract my qty, and update their price.
        earlier_id = earlier[0][0]
        cur.execute("UPDATE stock_ins SET unit_price=? WHERE id=?", (price, earlier_id))
        cur.execute("DELETE FROM stock_ins WHERE id=?", (sid,))
        cur.execute("UPDATE colors SET unopened = unopened - ? WHERE id=?", (qty, cid))
        print(f"Reverted duplicate insert {sid} and updated price to {price}")
    else:
        # User didn`t have it, so my insert is valid! (Maybe they forgot to insert it)
        print(f"Kept valid insert {sid}")

conn.commit()

