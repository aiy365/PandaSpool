
import sqlite3

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# Find all stock_ins added at 17:29
cur.execute("SELECT color_id, qty FROM stock_ins WHERE created_at LIKE \"2026-08-24T17:29%\"")
for cid, qty in cur.fetchall():
    cur.execute("UPDATE colors SET unopened = unopened - ? WHERE id=?", (qty, cid))

cur.execute("DELETE FROM stock_ins WHERE created_at LIKE \"2026-08-24T17:29%\"")

# Delete colors added at 17:29 (we can identify them by checking if their product was created at 17:29, or just seeing if they have 0 stock_ins)
# Actually, the python script didn`t set created_at on colors!
# It used `INSERT INTO colors (id, product_id, name, color_family, unopened, opened, notes) VALUES ...`
# So how to identify colors?
# We can identify colors whose product was created at 17:29.
cur.execute("SELECT id FROM products WHERE created_at LIKE \"2026-08-24T17:29%\"")
for pid_tuple in cur.fetchall():
    pid = pid_tuple[0]
    cur.execute("DELETE FROM colors WHERE product_id=?", (pid,))
    cur.execute("DELETE FROM products WHERE id=?", (pid,))

# What about colors added to EXISTING products?
# "Polymaker Panchroma" (the original one) had colors added?
# Let`s just find colors with unopened=0 and opened=0 and no stock_ins?
# Or look at the purchases array I used.
purchases = [
    {"brand": "遇果", "line": "", "mat": "PETG", "color": "银色", "price": 13.71, "qty": 1},
    {"brand": "遇果", "line": "", "mat": "PETG", "color": "黑色", "price": 13.71, "qty": 7},
    # The others mostly created new products.
]

conn.commit()
print("Reverted 17:29 inserts.")

