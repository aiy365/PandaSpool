import json, sqlite3, os
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
db.row_factory = sqlite3.Row
print("===PRODUCTS===")
for r in db.execute("select id,brand,product_line,material from products"):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===COLORS===")
for r in db.execute("select id,product_id,name,color_family,unopened,opened from colors"):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===INBOX===")
for r in db.execute("select id,product_id,IFNULL(color_id,'' ) as color_id,name,sha256,mime,size,status,created_at from inbox order by created_at"):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===CLAIMS===")
for r in db.execute("select id,product_id,source,claim_key,claim_value,unit,status from claims"):
    print(json.dumps(dict(r), ensure_ascii=False))
print("===SETTINGS AI===")
row = db.execute("select v from settings where k='app'").fetchone()
if row:
    s = json.loads(row[0])
    print(s.get("ai", {}).get("token", ""))
