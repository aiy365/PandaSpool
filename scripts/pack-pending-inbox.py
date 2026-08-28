#!/usr/bin/env python3
import os, sqlite3, shutil, tarfile

db = sqlite3.connect("/var/lib/printpilot/app.sqlite3")
db.row_factory = sqlite3.Row
out = "/tmp/inbox-pending"
os.makedirs(out, exist_ok=True)
src = "/var/lib/printpilot/files/inbox"
for r in db.execute(
    """
    select i.sha256, i.name, p.brand, p.product_line, p.material
    from inbox i join products p on p.id=i.product_id
    where i.status='pending'
    """
):
    brand = (r["brand"] or "").replace("/", "-")
    line = (r["product_line"] or "").replace("/", "-")
    mat = (r["material"] or "").replace("/", "-")
    dest = f"{out}/{brand}_{line}_{mat}_{r['name']}"
    shutil.copy2(os.path.join(src, r["sha256"]), dest)
    print(dest)
tgz = "/tmp/inbox-pending.tgz"
with tarfile.open(tgz, "w:gz") as tar:
    tar.add(out, arcname="inbox-pending")
print("packed", tgz)
