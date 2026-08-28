#!/usr/bin/env python3
"""Apply extracted colors (catalog) and param drafts from inbox images. Idempotent."""
import json, sqlite3, time, os, secrets
from datetime import datetime, timezone

DB = "/var/lib/pandaspool/app.sqlite3"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

P = {
    "r3d": "091e47913906cd1eb38e2e2eae0eb425",
    "poly_petg": "6138b9be8d4b4a5f67a05ffe9a8dc4b6",
    "panchroma": "2d2ac091692cf7ac51a2a0f263f5c464",
    "marble": "6ab0d72faae6d9994dc69dfdb06ab265",
    "kex": "19e970e50e56f851a4323ba135cac5e4",
    "sanyu": "70a7c4ee8bbda8fa599a6b2247929ddd",
    "biqu": "7ccadea97d2d3fae43625a4a1594410c",
    "dj_hf": "f3e1fd89c5e297d01ac2626517bb57fa",
    "dj_matte": "b1f2217bf4e1d27817c4ddfcc3c13bcf",
    "bambu_petg": "a634408a318f50dcf5f56b0816ffbcd2",
    "bambu_pla": "cb2f24e169f3e4fcec0159d60465fc63",
}

FAMILY = {
    "白": "白色系", "黑": "黑灰色系", "灰": "黑灰色系", "蓝": "蓝色系", "青": "蓝色系",
    "绿": "绿色系", "红": "红粉色系", "粉": "红粉色系", "桃": "红粉色系", "黄": "黄橙色系",
    "橙": "黄橙色系", "棕": "棕米色系", "咖": "棕米色系", "肤": "棕米色系", "米": "棕米色系",
    "紫": "紫色系", "金": "金属色系", "银": "金属色系", "铜": "金属色系", "透明": "透明/自然色系",
    "木": "棕米色系", "夜": "黑灰色系", "骨": "白色系", "瓷": "白色系",
}

def family(name):
    for k, v in FAMILY.items():
        if k in name:
            return v
    return "未分类"

def nid():
    return secrets.token_hex(16)

db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
db.execute("PRAGMA foreign_keys=ON")

def existing_colors(pid):
    return {r["name"]: r["id"] for r in db.execute("select id,name from colors where product_id=?", (pid,))}

def add_color(pid, name, extra_notes=""):
    name = name.strip()
    if not name:
        return None
    have = existing_colors(pid)
    if name in have:
        return have[name]
    cid = nid()
    db.execute(
        "insert into colors(id,product_id,name,color_family,unopened,opened,notes) values(?,?,?,?,0,0,?)",
        (cid, pid, name, family(name), extra_notes),
    )
    return cid

def add_claim(pid, source, key, value, unit="", raw="", color_id="", status="draft"):
    value = str(value).strip()
    if not key or not value:
        return
    color_id = color_id or ""
    row = db.execute(
        "select id from claims where product_id=? and ifnull(color_id,'')=? and source=? and claim_key=? and claim_value=? and unit=? and status!='rejected'",
        (pid, color_id, source, key, value, unit),
    ).fetchone()
    if row:
        return
    db.execute(
        "insert into claims(id,product_id,color_id,source,claim_key,claim_value,unit,raw,status,created_at) values(?,?,?,?,?,?,?,?,?,?)",
        (nid(), pid, color_id or None, source, key, value, unit, raw, status, NOW),
    )

def mark(ids):
    for i in ids:
        db.execute("update inbox set status='processed' where id=?", (i,))

# --- colors ---
poly_petg_colors = ["黑色","白色","灰色","红色","洋红色","橙色","黄色","绿色","深绿色","青色","蓝色","深蓝色","电光蓝","紫色","深紫色","粉色","银色"]
panchroma_colors = ["白色","灰色","钢铁灰","红色","蓝色","黑色","绿色","紫色","黄色","酒红色","青色","天蓝色","棕色","浅褐色","深橄榄色","深灰色"]
marble_colors = ["碳墨黑","棉花白","岩石灰","日落橙","森林绿","宝石蓝","蜜桃橙","香蕉黄","薄荷绿","糖果粉","樱花粉","冰蓝色","土壤棕","花生褐"]
kex_colors = ["黑色","白色","透明白色","奶油绿","星雾紫","肉粉色","薄荷绿","摩卡棕","苔藓绿","落日橙","柔粉色","蓝色","绿色","灰色","黄色","红色","银色","金属紫","太空灰"]
sanyu_shelf = ["黑","白","灰","正黄","橙","肤","银","蓝灰","仿木","黄","紫红","金","绿","草绿","蓝","红","紫"]
sanyu_new = ["白色","咖棕色","红色","黄色","明黄色","绿色","青色","克莱因蓝","薰衣草紫","品红色","黑色","肤色","灰色","橡木色","橄榄绿","阳光橙","瓷白色","骨白(高亮)","暗夜黑","栗黑"]
dj_hf = ["白色","黑色","灰色","透明色","橙色","黄色","樱花粉","银色","红色","米白色","金色","松石绿","透明蓝","透明绿","透明紫","薄荷绿","青色","粉红色","蓝灰色","杏色","拿铁色","苹果绿","暗金色","深蓝色","玫红色","绀紫色","紫罗兰","草绿色","青铜色","玫紫色"]
dj_matte = ["白色","黑色","灰色","棕色","红色","黄色"]
bambu_petg = ["白色","灰色","红色","黄色","深蓝色","深棕色","黑色","橙色","绿色","深米色","墨绿色","蓝灰色","湖蓝色"]
bambu_pla = ["白色","杏色","金色","银色","灰色","青铜色","棕色","红色","品红色","粉色","橙色","黄色","拓竹绿","墨绿色","青色","深蓝色","紫色","蓝灰色","黑色","浅灰色","暖黄色","苹果绿色","南瓜橙色","桃红色","松石绿色","钴蓝色","深灰色","可可棕色","胭脂红色","绀紫色","圣诞绿"]

for n in poly_petg_colors:
    add_color(P["poly_petg"], n)
for n in panchroma_colors:
    add_color(P["panchroma"], n)
for n in marble_colors:
    add_color(P["marble"], n)
for n in kex_colors:
    add_color(P["kex"], n)
for n in sanyu_shelf + sanyu_new:
    add_color(P["sanyu"], n)
for n in dj_hf:
    add_color(P["dj_hf"], n)
for n in dj_matte:
    add_color(P["dj_matte"], n)
for n in bambu_petg:
    add_color(P["bambu_petg"], n)
for n in bambu_pla:
    add_color(P["bambu_pla"], n)
add_color(P["biqu"], "半透明")

# RGB for bambu PLA / PETG / kexcelled
rgb_pla = {
    "白色":"#FFFFFF","杏色":"#F7E6DE","金色":"#E4BD68","银色":"#A6A9AA","灰色":"#8E9089",
    "青铜色":"#847D48","棕色":"#9D432C","红色":"#C12E1F","品红色":"#EC008C","粉色":"#F55A74",
    "橙色":"#FF6A13","黄色":"#F4EE2A","拓竹绿":"#00AE42","墨绿色":"#164B35","青色":"#0086D6",
    "深蓝色":"#0A2989","紫色":"#5E43B7","蓝灰色":"#5B6579","黑色":"#000000","浅灰色":"#D1D3D5",
    "暖黄色":"#FEC600","苹果绿色":"#BECF00","南瓜橙色":"#FF9016","桃红色":"#F5547C","松石绿色":"#00B1B7",
    "钴蓝色":"#0056B8","深灰色":"#545454","可可棕色":"#6F5034","胭脂红色":"#9D2235","绀紫色":"#482960","圣诞绿":"#164B35",
}
rgb_petg = {
    "白色":"#FFFFFF","灰色":"#7F7E83","红色":"#D6001C","黄色":"#FCE300","深蓝色":"#001489",
    "深棕色":"#4F2C1D","黑色":"#000000","橙色":"#FF671F","绿色":"#009639","深米色":"#DBC8B6",
    "墨绿色":"#034638","蓝灰色":"#688197","湖蓝色":"#0086D6",
}
rgb_kex = {
    "肉粉色":"#E5D5D4","柔粉色":"#E4C6D4","星雾紫":"#8966BD","金属紫":"#744E82","太空灰":"#4C4440",
    "灰色":"#9DA2A3","银色":"#7A8085","薄荷绿":"#59BDC9","蓝色":"#011589","黑色":"#202322",
    "黄色":"#FCE300","落日橙":"#FC4C01","红色":"#D6011B","金":"#BA8459","摩卡棕":"#8D573A",
    "透明白色":"#FFFFFF","白色":"#FFFFFF","奶油绿":"#C4D5A4","绿色":"#009638","苔藓绿":"#284632",
}
for n, hexv in rgb_pla.items():
    cid = add_color(P["bambu_pla"], n)
    add_claim(P["bambu_pla"], "资料", "色值RGB", hexv, "", "拓竹色值表", cid)
for n, hexv in rgb_petg.items():
    cid = add_color(P["bambu_petg"], n)
    add_claim(P["bambu_petg"], "资料", "色值RGB", hexv, "", "拓竹色值表 基础PETG", cid)
for n, hexv in rgb_kex.items():
    cid = add_color(P["kex"], n)
    add_claim(P["kex"], "资料", "色值RGB", hexv, "", "KEXCELLED THE K5 PETG Rapid 色值参考", cid)

# product line tweaks
db.execute("update products set product_line=? where id=? and (product_line='' or product_line is null)", ("THE K5 PETG Rapid", P["kex"]))
db.execute("update products set product_line=? where id=? and product_line=''", ("PLA 半透明", P["biqu"]))
db.execute("update products set product_line=? where id=?", ("HF", P["dj_hf"]))
db.execute("update products set product_line=? where id=?", ("Matte", P["dj_matte"]))
db.execute("update products set product_line=? where id=? and product_line=''", ("通用", P["poly_petg"]))

# --- params as drafts ---
# R3D merchant
r3d = P["r3d"]
add_claim(r3d, "资料", "喷嘴温度", "230-260", "°C", "商家参数卡")
add_claim(r3d, "资料", "热床温度", "60-70", "°C", "商家参数卡 底板温度")
add_claim(r3d, "资料", "冷却风扇", "100", "%", "商家参数卡")
add_claim(r3d, "资料", "打印速度", "50-200", "mm/s", "商家参数卡")
add_claim(r3d, "资料", "烘干温度", "50", "°C", "商家参数卡")
add_claim(r3d, "资料", "底板材质", "软磁贴", "", "商家参数卡")
add_claim(r3d, "资料", "密度", "1.27", "g/cm³", "商家参数卡 物理性能")
add_claim(r3d, "资料", "热变形温度", "68", "°C", "商家参数卡")
add_claim(r3d, "资料", "熔融指数", "5.3", "g/10min", "商家参数卡")
add_claim(r3d, "资料", "维卡软化温度", "68", "°C", "商家参数卡")
add_claim(r3d, "资料", "拉伸强度", "55", "MPa", "商家参数卡 机械性能")
add_claim(r3d, "资料", "断裂伸长率", "17.3", "%", "商家参数卡")
add_claim(r3d, "资料", "弯曲强度", "77", "MPa", "商家参数卡")
add_claim(r3d, "资料", "抗冲击强度", "17", "J/m", "商家参数卡；单位是 J/m 不是 kJ/m²")
# Studio screenshot is Bambu PETG Basic, recorded as Studio 对照 not manufacturer of R3D
add_claim(r3d, "Studio", "流量比例", "0.94", "", "截图：Bambu PETG Basic @BBL A1M 0.4，对照用，不是 R3D 厂家预设")
add_claim(r3d, "Studio", "密度", "1.25", "g/cm³", "Bambu PETG Basic @A1 mini 0.4 对照")
add_claim(r3d, "Studio", "收缩", "100", "%", "Bambu PETG Basic 对照")
add_claim(r3d, "Studio", "喷嘴温度下限", "230", "°C", "Bambu PETG Basic 对照")
add_claim(r3d, "Studio", "喷嘴温度上限", "270", "°C", "Bambu PETG Basic 对照")
add_claim(r3d, "Studio", "喷嘴温度", "255", "°C", "Bambu PETG Basic 首层/其它层 对照")
add_claim(r3d, "Studio", "热床温度", "70", "°C", "Bambu PETG Basic 纹理PEI 对照")
add_claim(r3d, "Studio", "最大体积流量", "9", "mm³/s", "Bambu PETG Basic @A1 mini 对照")

# Polymaker PETG mechanical (厂家)
pp = P["poly_petg"]
add_claim(pp, "资料", "杨氏模量 XY", "2311.11±92.41", "MPa", "力学性能 PETG ISO 527")
add_claim(pp, "资料", "杨氏模量 Z", "2202.91±52.34", "MPa", "力学性能 PETG ISO 527")
add_claim(pp, "资料", "拉伸强度 XY", "47.96±4.88", "MPa", "力学性能 PETG；图中 Z 行 OCR 疑似排版错误，未录入 47=5.71")
add_claim(pp, "资料", "断裂伸长率 XY", "9.33±6.57", "%", "力学性能 PETG")
add_claim(pp, "资料", "断裂伸长率 Z", "3.54±2.33", "%", "力学性能 PETG")
add_claim(pp, "资料", "弯曲模量 XY", "2277.34±198.09", "MPa", "ISO 178")
add_claim(pp, "资料", "弯曲模量 Z", "1958.74±126.39", "MPa", "ISO 178")
add_claim(pp, "资料", "弯曲强度 XY", "80.08±3.53", "MPa", "ISO 178")
add_claim(pp, "资料", "弯曲强度 Z", "57.65±5.63", "MPa", "ISO 178")
add_claim(pp, "资料", "简支梁冲击强度 XY 缺口", "4.95±0.55", "kJ/m²", "ISO 179")
add_claim(pp, "资料", "简支梁冲击强度 XY 无缺口", "20.24±3.95", "kJ/m²", "ISO 179")
add_claim(pp, "资料", "简支梁冲击强度 Z 无缺口", "15.74±3.91", "kJ/m²", "ISO 179")
add_claim(pp, "资料", "线径", "1.75", "mm", "商品页 黑色 1.75mm 1kg")

# Panchroma PLA 普通
pc = P["panchroma"]
add_claim(pc, "资料", "密度", "1.30", "g/cm³", "打印参数表 普通列 23°C")
add_claim(pc, "资料", "维卡软化温度", "66", "°C", "打印参数表 普通列")
add_claim(pc, "资料", "拉伸模量 XY", "2515±71", "MPa", "打印参数表 普通列")
add_claim(pc, "资料", "拉伸强度 XY", "51.6±0.3", "MPa", "打印参数表 普通列")
add_claim(pc, "资料", "拉伸强度 Z", "36.6±1.2", "MPa", "打印参数表 普通列")
add_claim(pc, "资料", "缺口冲击强度", "2.9±0.1", "kJ/m²", "打印参数表 普通列")
add_claim(pc, "资料", "打印温度", "190-230", "°C", "打印参数表")
add_claim(pc, "资料", "热床温度", "25-60", "°C", "打印参数表")
add_claim(pc, "资料", "打印速度", "<400", "mm/s", "普通列；另外两列被遮挡标为 <300")
add_claim(pc, "资料", "干燥建议", "55°C 6h", "", "打印参数表")

# Marble 哑光 column only (other columns redacted)
mb = P["marble"]
add_claim(mb, "资料", "密度", "1.37", "g/cm³", "颜色范围表 哑光列；相邻列被涂抹未录入")
add_claim(mb, "资料", "维卡软化温度", "62", "°C", "哑光列")
add_claim(mb, "资料", "拉伸模量 XY", "2049±64", "MPa", "哑光列")
add_claim(mb, "资料", "拉伸强度 XY", "28.1±0.5", "MPa", "哑光列")
add_claim(mb, "资料", "拉伸强度 Z", "15.4±0.2", "MPa", "哑光列")
add_claim(mb, "资料", "缺口冲击强度", "10.0±0.8", "kJ/m²", "哑光列；高于普通 Panchroma PLA 的 2.9")
add_claim(mb, "资料", "打印温度", "190-230", "°C", "与普通 Panchroma 相同行")
add_claim(mb, "资料", "热床温度", "25-60", "°C", "与普通 Panchroma 相同行")
add_claim(mb, "资料", "干燥建议", "55°C 6h", "", "")

# kexcelled
kx = P["kex"]
add_claim(kx, "资料", "产品型号", "THE K5 PETG Rapid", "", "参数页标题")
add_claim(kx, "资料", "线径", "1.75", "mm", "")
add_claim(kx, "资料", "线径公差", "±0.03", "mm", "")
add_claim(kx, "资料", "密度", "1.29~1.31", "g/cm³", "ISO 1183")
add_claim(kx, "资料", "熔融指数", "5~10", "g/10min", "ISO 1133；230°C / 2.16kg")
add_claim(kx, "资料", "热变形温度", "70", "°C", "ISO 75；弯曲应力 0.45MPa")
add_claim(kx, "资料", "维卡软化温度", "83", "°C", "ISO 306；10N")
add_claim(kx, "资料", "拉伸强度", "39~47", "MPa", "ISO 527")
add_claim(kx, "资料", "断裂伸长率", "7~10", "%", "图注标准写 ISO 178，与拉伸伸长率常见 ISO 527 不一致，原文照录")
add_claim(kx, "资料", "弯曲强度", "68~81", "MPa", "ISO 178")
add_claim(kx, "资料", "弯曲模量", "1900~2300", "MPa", "ISO 178")
add_claim(kx, "资料", "无缺口冲击强度", "32~39", "kJ/m²", "ISO 179")
add_claim(kx, "资料", "缺口冲击强度", "3~5", "kJ/m²", "ISO 179")
add_claim(kx, "资料", "喷嘴温度", "235-275", "°C", "建议打印参数")
add_claim(kx, "资料", "喷嘴口径", "0.4及以上", "mm", "")
add_claim(kx, "资料", "热床温度", "60-80", "°C", "")
add_claim(kx, "资料", "冷却风扇", "30-70", "%", "")
add_claim(kx, "资料", "打印速度", "40-300", "mm/s", "")
add_claim(kx, "资料", "回抽距离", "0.5-5", "mm", "")
add_claim(kx, "资料", "回抽速度", "30-70", "mm/s", "")
add_claim(kx, "资料", "烘干温度", "65-70", "°C", "8-12小时")
add_claim(kx, "资料", "底板材质", "玻璃平台、PEI底板、平台贴纸都可", "", "")

# 三绿
sy = P["sanyu"]
add_claim(sy, "资料", "线径", "1.75", "mm", "±0.02mm")
add_claim(sy, "资料", "线径公差", "±0.02", "mm", "")
add_claim(sy, "资料", "净重", "1", "kg", "±20g")
add_claim(sy, "资料", "喷嘴温度", "205-215", "°C", "PLA+2.0 建议打印参数")
add_claim(sy, "资料", "热床温度", "50-60", "°C", "")
add_claim(sy, "资料", "冷却风扇", "ON", "", "")
add_claim(sy, "资料", "打印速度", "50-100", "mm/s", "")
add_claim(sy, "资料", "烘干温度", "50", "°C", "打印前 4-6 小时")
add_claim(sy, "资料", "底板材质", "常规", "", "")
add_claim(sy, "资料", "密度", "1.21", "g/cm³", "")
add_claim(sy, "资料", "热变形温度", "56±3", "°C", "")
add_claim(sy, "资料", "熔融指数", "8.3±2", "g/10min", "")
add_claim(sy, "资料", "维卡软化温度", "54", "°C", "")
add_claim(sy, "资料", "拉伸强度", "46±5", "MPa", "")
add_claim(sy, "资料", "断裂伸长率", "10±2.5", "%", "")
add_claim(sy, "资料", "弯曲强度", "83±5", "MPa", "")
add_claim(sy, "资料", "缺口冲击强度", "10±3", "kJ/m²", "")

# 必趣
bq = P["biqu"]
add_claim(bq, "资料", "产品名称", "BIQU PLA 半透明", "", "")
add_claim(bq, "资料", "线径", "1.75±0.03", "mm", "")
add_claim(bq, "资料", "净重", "1", "kg", "")
add_claim(bq, "资料", "密度", "1.22", "g/cm³", "")
add_claim(bq, "资料", "热变形温度", ">54", "°C", "")
add_claim(bq, "资料", "拉伸强度", "58.3", "MPa", "")
add_claim(bq, "资料", "断裂伸长率", "3.8", "%", "")
add_claim(bq, "资料", "弯曲模量", "3110", "MPa", "")
add_claim(bq, "资料", "弯曲强度", "87.9", "MPa", "")
add_claim(bq, "资料", "冲击强度", "17", "kJ/m²", "")
add_claim(bq, "资料", "熔体流动速率", "15.7", "g/10min", "")
add_claim(bq, "资料", "打印温度", "210-240", "°C", "")
add_claim(bq, "资料", "热床温度", "35-55", "°C", "")
add_claim(bq, "资料", "风扇转速", "50-100", "%", "")
add_claim(bq, "资料", "打印速度", "50-200", "mm/s", "")
add_claim(bq, "资料", "烘干温度", "55", "°C", "8小时")
add_claim(bq, "资料", "Studio对照", "兼容 Bambu PLA Basic 参数", "", "原文：切片时可选择此耗材预设")

# 大简 HF
hf = P["dj_hf"]
add_claim(hf, "资料", "密度", "1.27", "g/cm³", "产品性能参数 PETG HF")
add_claim(hf, "资料", "拉伸强度", "50", "MPa", "")
add_claim(hf, "资料", "拉伸模量", "2412", "MPa", "")
add_claim(hf, "资料", "弯曲强度", "75", "MPa", "")
add_claim(hf, "资料", "弯曲模量", "2205", "MPa", "")
add_claim(hf, "资料", "断裂伸长率", "8.2", "%", "")
add_claim(hf, "资料", "抗冲击强度", "32", "kJ/m²", "")
add_claim(hf, "资料", "邵氏硬度", "78.5", "Shore D", "")
add_claim(hf, "资料", "热变形温度", "75", "°C", "")
add_claim(hf, "资料", "吸水率", "0.11", "%", "")
add_claim(hf, "资料", "收缩率 X", "-0.1", "%", "XY方向")
add_claim(hf, "资料", "收缩率 Y", "0.3", "%", "XY方向")
add_claim(hf, "资料", "喷嘴温度", "225-255", "°C", "可使用拓竹默认工艺")
add_claim(hf, "资料", "热床温度", "70", "°C", "可使用拓竹默认工艺")
add_claim(hf, "资料", "冷却风扇", "10-40", "%", "")
add_claim(hf, "资料", "打印环境湿度", "≤20", "%RH", "")
add_claim(hf, "资料", "首层速度", "50", "mm/s", "拓竹默认工艺卡")
add_claim(hf, "资料", "外墙速度", "200", "mm/s", "")
add_claim(hf, "资料", "内墙速度", "300", "mm/s", "")
add_claim(hf, "资料", "填充速度", "270", "mm/s", "")
add_claim(hf, "资料", "流量比例", "0.95", "", "选 Bambu PETG Basic 后修改；透明款为 1")
add_claim(hf, "资料", "流量比例 透明款", "1", "", "与普通款 0.95 不同")
add_claim(hf, "资料", "最大体积流量 A1", "9", "mm³/s", "A1 系列")
add_claim(hf, "资料", "最大体积流量 高速机", "13", "mm³/s", "P1/P2S/X1/H2S/H2D/H2C")
add_claim(hf, "资料", "打印温度", "240", "°C", "首层与其他层；与另一张卡 225-255 冲突，并存")
add_claim(hf, "资料", "热床温度", "70", "°C", "可再调高 5-10")
add_claim(hf, "资料", "Studio对照", "软件里选择 Bambu PETG Basic 再改上述字段", "", "")

# 大简 Matte
mt = P["dj_matte"]
add_claim(mt, "资料", "密度", "1.22", "g/cm³", "Matte PETG")
add_claim(mt, "资料", "拉伸强度", "31", "MPa", "低于同店 HF 的 50")
add_claim(mt, "资料", "拉伸模量", "1380", "MPa", "低于 HF 2412")
add_claim(mt, "资料", "弯曲强度", "62", "MPa", "")
add_claim(mt, "资料", "弯曲模量", "2014", "MPa", "")
add_claim(mt, "资料", "断裂伸长率", "9.8", "%", "对比图 Matte PETG 9.8%；同图普通 PETG 8.2% 是对照不是本产品")
add_claim(mt, "资料", "抗冲击强度", "60", "kJ/m²", "对比图写 60J/m，性能表写 60 kJ/m²，单位冲突并存")
add_claim(mt, "资料", "抗冲击强度", "60", "J/m", "对比条形图单位 J/m")
add_claim(mt, "资料", "邵氏硬度", "73.5", "Shore D", "")
add_claim(mt, "资料", "热变形温度", "67", "°C", "")
add_claim(mt, "资料", "吸水率", "0.2", "%", "")
add_claim(mt, "资料", "收缩率 X", "-0.2", "%", "")
add_claim(mt, "资料", "收缩率 Y", "0.1", "%", "")

# 拓竹 PETG 2025
bp = P["bambu_petg"]
add_claim(bp, "资料", "弯曲强度 XY", "75", "MPa", "2025新版卡片")
add_claim(bp, "资料", "弯曲强度 Z", "56", "MPa", "层间强度")
add_claim(bp, "资料", "冲击强度 XY", "34.2", "kJ/m²", "韧性")
add_claim(bp, "资料", "密度", "1.25", "g/cm³", "产品参数")
add_claim(bp, "资料", "维卡软化温度", "69", "°C", "")
add_claim(bp, "资料", "热变形温度", "71", "°C", "")
add_claim(bp, "资料", "熔融温度", "N/A", "", "原文 N/A")
add_claim(bp, "资料", "熔融指数", "22.9±2.4", "g/10min", "")
add_claim(bp, "资料", "拉伸强度", "51±1", "MPa", "")
add_claim(bp, "资料", "断裂伸长率", "9.5±0.7", "%", "")
add_claim(bp, "资料", "弯曲模量", "1950±50", "MPa", "")
add_claim(bp, "资料", "弯曲强度", "75±3", "MPa", "与卡片 XY 75 一致，带公差")
add_claim(bp, "资料", "冲击强度", "34.2±4.1", "kJ/m²", "与卡片 34.2 一致，带公差")

# 拓竹 PLA Basic
bl = P["bambu_pla"]
add_claim(bl, "资料", "密度", "1.24", "g/cm³", "")
add_claim(bl, "资料", "维卡软化温度", "57", "°C", "")
add_claim(bl, "资料", "热变形温度", "57", "°C", "")
add_claim(bl, "资料", "熔融温度", "160", "°C", "")
add_claim(bl, "资料", "熔融指数", "23.2±3.5", "g/10min", "")
add_claim(bl, "资料", "拉伸强度", "35±4", "MPa", "")
add_claim(bl, "资料", "断裂伸长率", "12.2±1.8", "%", "")
add_claim(bl, "资料", "弯曲模量", "2750±160", "MPa", "")
add_claim(bl, "资料", "弯曲强度", "76±5", "MPa", "")
add_claim(bl, "资料", "冲击强度", "26.6±2.8", "kJ/m²", "")
add_claim(bl, "资料", "烘干 鼓风", "50°C 8h", "", "打印指南")
add_claim(bl, "资料", "烘干 X1热床", "60-70°C 12h", "", "")
add_claim(bl, "资料", "烘干 AMS 2 Pro", "55°C 8h", "", "")
add_claim(bl, "资料", "烘干 AMS HT", "55°C 8h", "", "")
add_claim(bl, "资料", "打印环境湿度", "<20", "%RH", "密封加干燥剂")
add_claim(bl, "资料", "热床温度", "35-65", "°C", "打印指引")
add_claim(bl, "资料", "喷嘴温度", "190-230", "°C", "打印指引")

# mark inbox processed
for r in db.execute("select id from inbox"):
    db.execute("update inbox set status='processed' where id=?", (r["id"],))

db.commit()
print("colors", db.execute("select count(*) from colors").fetchone()[0])
print("claims", db.execute("select count(*) from claims").fetchone()[0])
print("drafts", db.execute("select count(*) from claims where status='draft'").fetchone()[0])
print("inbox pending", db.execute("select count(*) from inbox where status='pending'").fetchone()[0])
