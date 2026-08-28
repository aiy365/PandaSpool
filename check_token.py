import sqlite3
conn = sqlite3.connect('app.sqlite3')
c = conn.cursor()
c.execute("SELECT * FROM settings WHERE k='bambu_token'")
print(c.fetchall())
