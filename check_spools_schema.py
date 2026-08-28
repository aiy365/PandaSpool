import sqlite3
conn = sqlite3.connect('prod.sqlite3')
c = conn.cursor()
c.execute("PRAGMA table_info(spools)")
for row in c.fetchall():
    print(row)
