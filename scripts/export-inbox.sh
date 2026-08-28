#!/bin/bash
set -e
OUT=/tmp/pp-inbox-export
rm -rf "$OUT"
mkdir -p "$OUT"
python3 - << 'PY'
import json, os, shutil, sqlite3
src = "/var/lib/pandaspool/files/inbox"
out = "/tmp/pp-inbox-export"
os.makedirs(out, exist_ok=True)
db = sqlite3.connect("/var/lib/pandaspool/app.sqlite3")
db.row_factory = sqlite3.Row
prods = {r["id"]: dict(r) for r in db.execute("select id,brand,product_line,material from products")}
manifest = []
for r in db.execute("select id,product_id,name,sha256,mime,status from inbox order by created_at"):
    p = prods.get(r["product_id"], {})
    brand = (p.get("brand") or "x").replace("/", "-")
    line = (p.get("product_line") or "").replace("/", "-")
    mat = (p.get("material") or "").replace("/", "-")
    folder = f"{brand}_{line}_{mat}_{r['product_id'][:8]}".replace(" ", "")
    dest_dir = os.path.join(out, folder)
    os.makedirs(dest_dir, exist_ok=True)
    ext = ".jpg"
    if "png" in (r["mime"] or ""):
        ext = ".png"
    elif "webp" in (r["mime"] or ""):
        ext = ".webp"
    dest = os.path.join(dest_dir, f"{r['id'][:8]}_{r['name']}")
    srcp = os.path.join(src, r["sha256"])
    if os.path.exists(srcp):
        shutil.copy2(srcp, dest)
    manifest.append({
        "inbox_id": r["id"], "product_id": r["product_id"],
        "brand": p.get("brand"), "product_line": p.get("product_line"),
        "material": p.get("material"), "name": r["name"],
        "file": dest, "status": r["status"],
    })
open(os.path.join(out, "manifest.json"), "w", encoding="utf-8").write(json.dumps(manifest, ensure_ascii=False, indent=2))
print(len(manifest), "files")
PY
tar -C /tmp -czf /tmp/pp-inbox-export.tgz pp-inbox-export
ls -lh /tmp/pp-inbox-export.tgz
