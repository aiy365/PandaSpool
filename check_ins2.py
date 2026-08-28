
import sqlite3
import pandas as pd
conn = sqlite3.connect("prod.sqlite3")
query = """
SELECT p.brand, p.product_line, c.name, s.qty, s.unit_price, s.created_at
FROM stock_ins s
JOIN colors c ON s.color_id = c.id
JOIN products p ON c.product_id = p.id
WHERE s.created_at LIKE "2026-08-19%" OR s.created_at LIKE "2026-08-24T17:41%"
ORDER BY p.brand, c.name, s.created_at
"""
print(pd.read_sql_query(query, conn).head(30))

