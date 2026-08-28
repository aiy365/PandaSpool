import sqlite3
conn = sqlite3.connect('prod.sqlite3')
c = conn.cursor()
c.execute("SELECT DISTINCT color_family FROM colors")
print([r[0] for r in c.fetchall()])
