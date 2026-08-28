#!/usr/bin/env python3
import re, sqlite3

DB = "/var/lib/pandaspool/app.sqlite3"
PID = "091e47913906cd1eb38e2e2eae0eb425"
hours_re = re.compile(r"(?i)(\d+(?:\s*[-~–—]\s*\d+)?)\s*(小时|h\b|hrs?\b|hours?\b)")

def compact(s):
    return s.replace(" ", "").replace("–", "-").replace("—", "-").replace("~", "-").strip()

def pretty_unit(u):
    u = (u or "").strip()
    if u.lower() in ("h", "hr", "hrs", "hour", "hours"):
        return "小时"
    return u

def fmt(value, unit):
    v = (value or "").strip()
    u = pretty_unit(unit)
    if not u:
        return v
    if u in v:
        return v
    if u == "小时" and (v.lower().endswith("h") or "小时" in v):
        return v
    return (v + u).strip()

def hours_from_raw(raw):
    m = hours_re.search(raw or "")
    if not m:
        return None
    return compact(m.group(1)), "小时"

def card_of(rows):
    best = {}
    for r in rows:
        if r["status"] not in ("", "confirmed"):
            continue
        if r["color_id"]:
            continue
        if r["source"] == "Studio":
            continue
        old = best.get(r["claim_key"])
        if not old or (r["created_at"] or "") >= (old["created_at"] or ""):
            best[r["claim_key"]] = r
    def pick(*keys):
        for k in keys:
            if k in best and (best[k]["claim_value"] or "").strip():
                return best[k]
        return None
    out = {}
    t = pick("烘干温度范围", "烘干温度")
    h = pick("烘干时间")
    if t and not h:
        extra = hours_from_raw(t["raw"])
        if extra:
            h = {"claim_value": extra[0], "unit": extra[1]}
    combined = pick("烘干")
    if t and h:
        out["烘干"] = fmt(t["claim_value"], t["unit"]) + ", " + fmt(h["claim_value"], h["unit"])
    elif combined:
        out["烘干"] = fmt(combined["claim_value"], combined["unit"])
    elif t:
        out["烘干"] = fmt(t["claim_value"], t["unit"])
    n = pick("喷嘴温度范围", "喷嘴推荐温度")
    if n:
        out["喷嘴"] = fmt(n["claim_value"], n["unit"])
    b = pick("热床温度范围", "热床推荐温度")
    if b:
        out["热床"] = fmt(b["claim_value"], b["unit"])
    s = pick("打印速度上限", "打印速度范围", "打印速度")
    if s:
        out["速度"] = fmt(s["claim_value"], s["unit"])
    return out

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
print("===R3D CARD===")
rows = list(db.execute(
    "select claim_key,claim_value,unit,raw,status,source,ifnull(color_id,'') color_id,ifnull(created_at,'') created_at from claims where product_id=?",
    (PID,),
))
print(card_of(rows))
print("===ALL PRODUCT CARDS===")
for p in db.execute("select id,brand,product_line,material from products order by brand,product_line"):
    rows = list(db.execute(
        "select claim_key,claim_value,unit,raw,status,source,ifnull(color_id,'') color_id,ifnull(created_at,'') created_at from claims where product_id=?",
        (p["id"],),
    ))
    c = card_of(rows)
    if c:
        print(f"{p['brand']} {p['product_line']} {p['material']}: {c}")
print("===INBOX PENDING===")
for r in db.execute("select id,name,status from inbox where status!='processed'"):
    print(dict(r))
