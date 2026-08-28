import sqlite3
conn = sqlite3.connect('app.sqlite3')
c = conn.cursor()
c.execute("SELECT k FROM settings")
print(c.fetchall())
