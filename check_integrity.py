
import sqlite3
conn = sqlite3.connect("prod.sqlite3")
cur = conn.cursor()
cur.execute("PRAGMA integrity_check;")
print(cur.fetchall())

