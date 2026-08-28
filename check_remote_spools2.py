import sqlite3
conn = sqlite3.connect('app_remote.sqlite3')
c = conn.cursor()
c.execute("SELECT id, bambu_cloud_id, bambu_filament_name FROM spools WHERE bambu_cloud_id > 0")
rows = c.fetchall()
print(f"Total spools to delete: {len(rows)}")
for r in rows:
    print(r)
