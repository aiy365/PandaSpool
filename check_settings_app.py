import sqlite3
import json
conn = sqlite3.connect('app.sqlite3')
c = conn.cursor()
c.execute("SELECT v FROM settings WHERE k='app'")
print(c.fetchone()[0])
