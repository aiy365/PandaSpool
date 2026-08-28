import json, sqlite3
db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
raw = db.execute("select v from settings where k='app'").fetchone()[0]
s = json.loads(raw)
ew = s.get("ewelink", {})
print("light", ew.get("light"))
print("box_always", ew.get("box_always"))
print("box_print", ew.get("box_print"))
print("room", ew.get("room"))
print("boost_min", (s.get("automations") or {}).get("print_boost_minutes"))
print("box_always_on", (s.get("automations") or {}).get("box_always_on"))
