
import sqlite3
import pandas as pd

conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()

# Get total unopened and opened
cur.execute("SELECT SUM(unopened), SUM(opened) FROM colors")
print("Total Unopened, Opened:", cur.fetchone())

# Let`s group by product to see where the huge numbers are
query = """
SELECT p.brand, p.product_line, p.material, c.name, c.unopened, c.opened
FROM colors c
JOIN products p ON c.product_id = p.id
ORDER BY c.unopened DESC
LIMIT 20;
"""
df = pd.read_sql_query(query, conn)
print(df)

