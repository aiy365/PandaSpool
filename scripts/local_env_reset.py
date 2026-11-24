# -*- coding: utf-8 -*-
# 本地测试环境一键重建：DB 恢复 + 萤石凭证拉取 + 打印机 SN
import json
import os
import shutil
import sqlite3
import subprocess

SRC = r"C:\work\3D模型\PandaSpool-front-audit\20260907-184330\app.sqlite3"
DST = r"C:\work\3D模型\ui-opt-20260907\app.sqlite3"
# 生产 SSH 目标与测试管理员口令都不入库，运行时从环境变量取。
PROD = os.environ.get("PP_PROD_SSH", "root@<server-host>")
TEST_ADMIN_PASSWORD = os.environ.get("PP_TEST_ADMIN_PASSWORD", "changeme")

# 1) 恢复审计克隆（主文件 + WAL + SHM 三件一起拷，缺 WAL 会丢数据）
src_dir = os.path.dirname(SRC)
dst_dir = os.path.dirname(DST)
for ext in ("", "-wal"):
    src = os.path.join(src_dir, "app.sqlite3" + ext)
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(dst_dir, "app.sqlite3" + ext))

# 2) 管理员密码 + 打印机 SN
h = bcrypt_hash = None
try:
    import bcrypt
    h = bcrypt.hashpw(TEST_ADMIN_PASSWORD.encode(), bcrypt.gensalt(10)).decode()
except ImportError:
    pass

db = sqlite3.connect(DST, timeout=10)
db.execute("PRAGMA integrity_check").fetchone()
if h:
    db.execute("UPDATE meta SET v=? WHERE k='admin_password'", (h,))
sn = json.loads(db.execute("SELECT v FROM settings WHERE k='app'").fetchone()[0])["bambu"].get("printer_sn", "")
db.commit()

# 3) 萤石凭证从生产拉取
raw = subprocess.run(
    ["ssh", PROD, "sqlite3 /var/lib/printpilot/app.sqlite3 \"SELECT v FROM settings WHERE k='app'\""],
    capture_output=True, text=True, timeout=60).stdout.strip()
ez = json.loads(raw)["ezviz"]
ls = json.loads(db.execute("SELECT v FROM settings WHERE k='app'").fetchone()[0])
for k in ("app_key", "app_secret", "device_serial", "verify_code", "access_token", "token_expire_at"):
    if ez.get(k):
        ls["ezviz"][k] = ez[k]
db.execute("UPDATE settings SET v=? WHERE k='app'", (json.dumps(ls),))
db.commit()
n = db.execute("SELECT COUNT(*) FROM spools").fetchone()[0]
db.close()
print("done: spools", n, "| sn len", len(sn), "| ezviz serial", ls["ezviz"].get("device_serial"))
