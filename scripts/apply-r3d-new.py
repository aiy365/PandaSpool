#!/usr/bin/env python3
import secrets, sqlite3
from datetime import datetime, timezone

DB = "/var/lib/pandaspool/app.sqlite3"
PID = "091e47913906cd1eb38e2e2eae0eb425"
INBOX = "a52ea438bdbdd9f625b42ffe06aa3706"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
RAW = "推荐打印条件 / 耗材特性 1000038942"

CLAIMS = [
    ("烘干温度范围", "60-65", "°C"),
    ("烘干时间", "4-8", "小时"),
    ("烘干", "60-65°C, 4-8小时", ""),
    ("需要烘干", "是", ""),
    ("AMS兼容", "是", ""),
    ("喷嘴尺寸", "0.3-0.8", "mm"),
    ("喷嘴材质", "铜/硬化钢", ""),
    ("封箱", "否", ""),
    ("打印速度上限", "<300", "mm/s"),
    ("冷却风扇", "10-40", "%"),
    ("喷嘴温度范围", "230-260", "°C"),
    ("热床温度范围", "70-90", "°C"),
    ("回抽距离", "2-4", "mm"),
    ("回抽速度", "30-45", "mm/s"),
    ("密度", "1.27", "g/cm³"),
    ("熔融指数", "4.86", "g/10min"),
    ("拉伸强度 XY", "41", "MPa"),
    ("弯曲强度 XY", "68", "MPa"),
    ("弯曲模量 XY", "2079", "MPa"),
    ("冲击强度 Z 缺口", "1.85", "kJ/m²"),
    ("维卡软化温度", "77", "°C"),
    ("热变形温度", "68.4", "°C"),
]

db = sqlite3.connect(DB)
n = 0
for key, value, unit in CLAIMS:
    row = db.execute(
        "select id from claims where product_id=? and ifnull(color_id,'')='' and source='资料' and claim_key=? and claim_value=? and unit=? and status!='rejected'",
        (PID, key, value, unit),
    ).fetchone()
    if row:
        continue
    db.execute(
        "insert into claims(id,product_id,color_id,source,claim_key,claim_value,unit,raw,status,created_at) values(?,?,?,?,?,?,?,?,?,?)",
        (secrets.token_hex(16), PID, None, "资料", key, value, unit, RAW, "confirmed", NOW),
    )
    n += 1
    print("OK", key, value, unit)
db.execute("update inbox set status='processed' where id=?", (INBOX,))
db.commit()
print("inserted", n)
db.close()
