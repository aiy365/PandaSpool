
import sqlite3
import pandas as pd
conn = sqlite3.connect("prod.sqlite3")
query = """
SELECT p.brand, p.product_line, c.name, s.qty, s.created_at
FROM stock_ins s
JOIN colors c ON s.color_id = c.id
JOIN products p ON c.product_id = p.id
WHERE p.brand="大简" AND c.name="深灰色"
"""
print(pd.read_sql_query(query, conn))

