
import sqlite3
import pandas as pd
conn = sqlite3.connect("prod.sqlite3")
query = "SELECT name, color_family, unopened FROM colors WHERE unopened > 0 LIMIT 20"
print(pd.read_sql_query(query, conn))

