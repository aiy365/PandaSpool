#!/usr/bin/env python3
"""Extract pending inbox images into draft claims. 厂家/商家一律记资料。不新建颜色、不改库存。"""
import secrets
import sqlite3
from datetime import datetime, timezone

DB = "/var/lib/printpilot/app.sqlite3"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
SRC = "资料"

P = {
    "tianwei": "e67ce04e60e9c691325962ff0599a5f5",
    "bambu_matte": "dccccccf8f4c5dfc32cb0770db448d00",
    "bambu_lite": "4e13903217d281cbc482ee5182c40276",
    "sanyu_matte": "26fbf5e0f6e3b14d236b8d35dabace62",
}

PENDING = [
    "78d12fbc54fa3abc071bc89c42f996ff",
    "0fd4a3777ba313aff0eb7980a0f6deb5",
    "6a066c280db84f55811b67080028a75a",
    "90fca02c33dc11a8f2bc728f182855d7",
    "166130cef65a4866d45c9e91974f5edc",
    "1e8a030c688ddc7022b3b3fd6e66d143",
    "e93e1da9293a26119340a9f5f78fd600",
    "aa2c68c867d5b6c7891ffa5602fe457d",
    "dad0e6ccf9432e0e1c32d0f0623a0fbb",
    "f7f1c88bdfab84f921c87281981ff285",
    "9047998f8b6100f191efbcf105cd6af0",
    "8adf83a92893c30e0a24dedd1e1311ee",
]


def nid():
    return secrets.token_hex(16)


db = sqlite3.connect(DB)
db.row_factory = sqlite3.Row
n = 0


def add_claim(pid, key, value, unit="", raw="", source=SRC):
    global n
    value = str(value).strip()
    if not key or not value:
        return
    row = db.execute(
        "select id from claims where product_id=? and ifnull(color_id,'')='' and source=? and claim_key=? and claim_value=? and unit=? and status!='rejected'",
        (pid, source, key, value, unit),
    ).fetchone()
    if row:
        return
    db.execute(
        "insert into claims(id,product_id,color_id,source,claim_key,claim_value,unit,raw,status,created_at) values(?,?,?,?,?,?,?,?,?,?)",
        (nid(), pid, None, source, key, value, unit, raw, "draft", NOW),
    )
    n += 1


# --- 天威 PLA Basic 1000038924 ---
tw = P["tianwei"]
add_claim(tw, "材质", "PLA-Basic", "", "PLA-Basic 基本参数卡")
add_claim(tw, "净重", "1", "kg", "")
add_claim(tw, "线径", "1.75", "mm", "")
add_claim(tw, "中心孔直径", "5.3", "cm", "")
add_claim(tw, "线径公差", "±0.02", "mm", "")
add_claim(tw, "喷嘴温度", "190-210", "°C", "打印参数")
add_claim(tw, "热床温度", "60-70", "°C", "图上写平台温度")
add_claim(tw, "热变形温度", "50", "°C", "")
add_claim(tw, "弯曲强度", "15000", "MPa", "图上 15000Mpa，数量级异常，疑似笔误或把弯曲模量写错栏")
add_claim(tw, "断裂伸长率", "≥5.0", "%", "")
add_claim(tw, "缺口冲击强度", "≥3.6", "kJ/m", "图上单位 KJM/m，不是 kJ/m²")

# --- 拓竹 PLA Matte 8925 产品参数 + 8926 打印指引 ---
bm = P["bambu_matte"]
add_claim(bm, "密度", "1.31", "g/cm³", "商品快照 产品参数")
add_claim(bm, "维卡软化温度", "63", "°C", "")
add_claim(bm, "热变形温度", "58", "°C", "商品快照未写载荷")
add_claim(bm, "熔融温度", "163", "°C", "")
add_claim(bm, "熔融指数", "18.0±3.2", "g/10min", "")
add_claim(bm, "拉伸强度", "30±5", "MPa", "")
add_claim(bm, "断裂伸长率", "14.8±4.2", "%", "")
add_claim(bm, "弯曲模量", "2360±250", "MPa", "")
add_claim(bm, "弯曲强度", "53±6", "MPa", "")
add_claim(bm, "冲击强度", "19.2±3.7", "kJ/m²", "")
add_claim(bm, "烘干 鼓风", "50°C 8h", "", "打印指南 / 打印指引")
add_claim(bm, "烘干 X1热床", "60-70°C 12h", "", "")
add_claim(bm, "烘干 AMS 2 Pro", "55°C 8h", "", "")
add_claim(bm, "烘干 AMS HT", "55°C 8h", "", "")
add_claim(bm, "打印环境湿度", "<20", "%RH", "密封，加干燥剂")
add_claim(bm, "热床温度", "35-65", "°C", "打印指引")
add_claim(bm, "喷嘴温度", "190-230", "°C", "打印指引")

# --- 拓竹 PLA Lite ---
bl = P["bambu_lite"]
# 8928 对比表：预设两行是 Studio 数值，其余记资料。不把 Basic/Matte 列写进 Lite。
add_claim(bl, "外观质感", "哑光", "", "PLA 类耗材对比")
add_claim(bl, "喷嘴适配", "0.2 / 0.4 / 0.6 / 0.8", "mm", "")
add_claim(bl, "预设打印温度", "220", "°C", "对比表「预设」行，按 Studio 记", "Studio")
add_claim(bl, "预设最高体积速度", "16", "mm³/s", "对比表「预设最高体积速度」，按 Studio 记", "Studio")
add_claim(bl, "弯曲强度 XY", "51", "MPa", "对比表 强度（弯曲强度-XY方向）")
add_claim(bl, "冲击强度 Z", "5.5", "kJ/m²", "对比表 层间粘接（冲击强度-Z方向）")

# 8930 商品页产品参数（熔融指数单位按图照录，和 TDS 冲突并存）
add_claim(bl, "密度", "1.4", "g/cm³", "商品页产品参数")
add_claim(bl, "维卡软化温度", "61", "°C", "商品页")
add_claim(bl, "热变形温度", "60", "°C", "商品页未写载荷；TDS 另有 1.8/0.45 MPa 两档")
add_claim(bl, "熔融温度", "160", "°C", "商品页")
add_claim(bl, "熔融指数", "13.8", "g/cm³", "商品页单位写成 g/cm³，疑似笔误")
add_claim(bl, "拉伸强度", "32±5", "MPa", "商品页")
add_claim(bl, "断裂伸长率", "11.2±3.1", "%", "商品页")
add_claim(bl, "弯曲强度", "51±3", "MPa", "商品页")
add_claim(bl, "弯曲模量", "2240±120", "MPa", "商品页")
add_claim(bl, "冲击强度", "19.0±3.7", "kJ/m²", "商品页，对应 TDS 的 XY 无缺口")
add_claim(bl, "烘干 鼓风", "50°C 8h", "", "打印指南 / 打印指引 / 推荐打印设置")
add_claim(bl, "烘干 X1热床", "60-70°C 12h", "", "")
add_claim(bl, "打印环境湿度", "<20", "%RH", "密封，加干燥剂")
add_claim(bl, "热床温度", "35-65", "°C", "打印指引 / 打印面板温度")
add_claim(bl, "喷嘴温度", "190-240", "°C", "打印指引 / 推荐打印设置")

# 8932 规格 + 推荐打印设置
add_claim(bl, "线径", "1.75±0.03", "mm", "规格表")
add_claim(bl, "净重", "1", "kg", "")
add_claim(bl, "料盘材料", "ABS（耐温 70°C）", "", "")
add_claim(bl, "料盘尺寸", "直径 200 mm；高度 67 mm", "", "")
add_claim(bl, "喷嘴尺寸", "0.2 / 0.4 / 0.6 / 0.8", "mm", "推荐打印设置")
add_claim(bl, "打印面板类型", "纹理 PEI / 光面 PEI / 低温增强打印板", "", "")
add_claim(bl, "冷却风扇", "开", "", "")
add_claim(bl, "打印速度", "<250", "mm/s", "")
add_claim(bl, "回抽距离", "0.6-1.0", "mm", "")
add_claim(bl, "回抽速度", "20-40", "mm/s", "")
add_claim(bl, "打印环境温度", "25-40", "°C", "")
add_claim(bl, "最大悬垂角", "55", "°", "")
add_claim(bl, "最大桥接长度", "30", "mm", "")
add_claim(bl, "支撑", "PLA 专用支撑耗材", "", "")

# 8933 物理性能 TDS
add_claim(bl, "密度", "1.40", "g/cm³", "物理性能 ISO 1183")
add_claim(bl, "熔融指数", "13.8", "g/10min", "210°C, 2.16 kg")
add_claim(bl, "玻璃化转变温度", "53", "°C", "DSC 10°C/min")
add_claim(bl, "结晶温度", "N/A", "", "DSC 10°C/min")
add_claim(bl, "热变形温度 1.8 MPa", "56", "°C", "ISO 75")
add_claim(bl, "热变形温度 0.45 MPa", "60", "°C", "ISO 75")
add_claim(bl, "饱和吸水率", "0.26", "%", "25°C, 55% RH")

# 8934 机械性能 TDS
add_claim(bl, "杨氏模量 XY", "2170±190", "MPa", "ISO 527, GB/T 1040")
add_claim(bl, "杨氏模量 Z", "1750±150", "MPa", "ISO 527, GB/T 1040")
add_claim(bl, "拉伸强度 XY", "32±5", "MPa", "ISO 527, GB/T 1040")
add_claim(bl, "拉伸强度 Z", "16.7±4", "MPa", "ISO 527, GB/T 1040")
add_claim(bl, "断裂伸长率 XY", "11.2±3.1", "%", "ISO 527, GB/T 1040")
add_claim(bl, "断裂伸长率 Z", "4.6±1.7", "%", "ISO 527, GB/T 1040")
add_claim(bl, "弯曲模量 XY", "2240±120", "MPa", "ISO 178, GB/T 9341")
add_claim(bl, "弯曲模量 Z", "1980±140", "MPa", "ISO 178, GB/T 9341")
add_claim(bl, "弯曲强度 XY", "51±3", "MPa", "ISO 178, GB/T 9341")
add_claim(bl, "弯曲强度 Z", "27±4", "MPa", "ISO 178, GB/T 9341")
add_claim(bl, "简支梁冲击强度 XY", "19.0±3.7", "kJ/m²", "ISO 179, GB/T 1043")
add_claim(bl, "简支梁冲击强度 XY 缺口", "6.8±2.2", "kJ/m²", "ISO 179")
add_claim(bl, "简支梁冲击强度 Z", "5.5±1.2", "kJ/m²", "ISO 179")
add_claim(bl, "样条打印喷嘴温度", "210", "°C", "机械性能注")
add_claim(bl, "样条打印速度", "200", "mm/s", "")
add_claim(bl, "样条热床温度", "35", "°C", "")
add_claim(bl, "样条填充率", "100", "%", "")
add_claim(bl, "退火建议", "50-60°C 6-12h", "", "推荐退火温度")

# 8935 其他物理/化学
add_claim(bl, "颜色、状态", "红色、白色等，固体", "", "其他物理性能和化学性能；不是完整色卡")
add_claim(bl, "气味", "无味", "", "")
add_claim(bl, "成分", "聚乳酸", "", "")
add_claim(bl, "对皮肤毒性", "无", "", "")
add_claim(bl, "化学稳定性", "通常状态下稳定", "", "")
add_claim(bl, "溶解性", "不溶于水", "", "")
add_claim(bl, "耐酸性", "不耐", "", "")
add_claim(bl, "耐碱性", "不耐", "", "")
add_claim(bl, "耐有机溶剂性", "不耐部分有机溶剂", "", "")
add_claim(bl, "耐油脂性", "耐多数油脂", "", "")
add_claim(bl, "可燃性", "可燃", "", "")
add_claim(bl, "燃烧产物", "水、碳氧化物", "", "")
add_claim(bl, "燃烧产物的气味", "无气味", "", "")

# --- 三绿 PLA Matte 8937 ---
sm = P["sanyu_matte"]
add_claim(sm, "线径", "1.75", "mm", "PLA哑光 建议打印参数")
add_claim(sm, "线径公差", "±0.02", "mm", "")
add_claim(sm, "净重", "1", "kg", "±20g")
add_claim(sm, "喷嘴温度", "205-215", "°C", "")
add_claim(sm, "热床温度", "50-60", "°C", "图上写底板温度")
add_claim(sm, "冷却风扇", "ON", "", "")
add_claim(sm, "打印速度", "50-100", "mm/s", "")
add_claim(sm, "烘干温度", "50", "°C", "打印前 4-6 小时")
add_claim(sm, "底板材质", "常规", "", "")
add_claim(sm, "密度", "1.31", "g/cm³", "物理性能")
add_claim(sm, "热变形温度", "55±5", "°C", "")
add_claim(sm, "熔融指数", "5.5±1.5", "g/10min", "")
add_claim(sm, "维卡软化温度", "54", "°C", "")
add_claim(sm, "拉伸强度", "39±6", "MPa", "机械性能")
add_claim(sm, "断裂伸长率", "15±5", "%", "")
add_claim(sm, "弯曲强度", "72±6", "MPa", "")
add_claim(sm, "缺口冲击强度", "5±2", "kJ/m²", "")

for i in PENDING:
    db.execute("update inbox set status='processed' where id=?", (i,))

db.commit()
left = db.execute("select count(*) from inbox where status='pending'").fetchone()[0]
print("drafts_inserted", n, "inbox_pending_left", left)
db.close()
