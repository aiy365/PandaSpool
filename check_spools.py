import sqlite3
conn = sqlite3.connect('prod.sqlite3')
c = conn.cursor()
c.execute("SELECT COUNT(*), MIN(short_code), MAX(short_code) FROM spools")
print(c.fetchone())
