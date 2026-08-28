
import sqlite3
import pandas as pd
conn = sqlite3.connect("prod.sqlite3")
query = "SELECT color_family, SUM(unopened) FROM colors GROUP BY color_family"
print(pd.read_sql_query(query, conn))

