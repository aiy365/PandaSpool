import json, urllib.request, sqlite3, time, uuid

DB_PATH = "prod.sqlite3"
URL_BAMBU = "https://api.bambulab.cn/v1/design-user-service/my/filament/v2"
TOKEN = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"

COLORS = {
    "黑色": "#000000FF", "白色": "#FFFFFFFF", "红色": "#FF0000FF", "绿色": "#00FF00FF",
    "蓝色": "#0000FFFF", "黄色": "#FFFF00FF", "橙色": "#FFA500FF", "紫色": "#800080FF",
    "灰色": "#808080FF", "粉色": "#FFC0CBFF", "洋红色": "#FF00FFFF", "青色": "#00FFFFFF",
    "深绿色": "#006400FF", "深蓝色": "#00008BFF", "电光蓝": "#7DF9FFFF", "深紫色": "#301934FF",
    "银色": "#C0C0C0FF", "钢铁灰": "#434B4DFF", "酒红色": "#800020FF", "天蓝色": "#87CEEBFF",
    "棕色": "#A52A2AFF", "浅褐色": "#D2B48CFF", "深橄榄色": "#556B2FFF", "深灰色": "#A9A9A9FF",
    "碳墨黑": "#1C1C1CFF", "棉花白": "#F2F2F2FF", "岩石灰": "#9C9C9CFF", "日落橙": "#FD5E53FF",
    "森林绿": "#228B22FF", "宝石蓝": "#082567FF", "蜜桃橙": "#FFCBA4FF", "香蕉黄": "#FFE135FF",
    "薄荷绿": "#98FF98FF", "糖果粉": "#E4717AFF", "樱花粉": "#FFB7C5FF", "冰蓝色": "#99FFFFFF",
    "土壤棕": "#8B4513FF", "花生褐": "#C2B280FF", "透明白色": "#FFFFFF88", "奶油绿": "#90EE90FF",
    "星雾紫": "#B0C4DEFF", "肉粉色": "#FFD1DCFF", "摩卡棕": "#4E3822FF", "苔藓绿": "#8A9A5BFF",
    "落日橙": "#FF4E20FF", "柔粉色": "#FFB6C1FF", "金属紫": "#581845FF", "太空灰": "#414A4CFF",
    "黑": "#000000FF", "白": "#FFFFFFFF", "灰": "#808080FF", "正黄": "#FFFF00FF", "橙": "#FFA500FF",
    "肤": "#FFCBA4FF", "银": "#C0C0C0FF", "蓝灰": "#6699CCFF", "仿木": "#DEB887FF", "黄": "#FFFF00FF",
    "紫红": "#800080FF", "金": "#FFD700FF", "绿": "#00FF00FF", "草绿": "#7CFC00FF", "蓝": "#0000FFFF",
    "红": "#FF0000FF", "紫": "#800080FF", "咖棕色": "#6F4E37FF", "明黄色": "#FFEA00FF",
    "克莱因蓝": "#002FA7FF", "薰衣草紫": "#E6E6FAFF", "品红色": "#FF0090FF", "肤色": "#FFCBA4FF",
    "橡木色": "#DFB37BFF", "橄榄绿": "#808000FF", "阳光橙": "#FF7F00FF", "瓷白色": "#F2F2F2FF",
    "骨白(高亮)": "#F9F6EEFF", "暗夜黑": "#050505FF", "栗黑": "#2B2222FF", "透明色": "#FFFFFF55",
    "米白色": "#F5F5DCFF", "金色": "#FFD700FF", "松石绿": "#40E0D0FF", "透明蓝": "#0000FF88",
    "透明绿": "#00FF0088", "透明紫": "#80008088", "粉红色": "#FFC0CBFF", "蓝灰色": "#6699CCFF",
    "杏色": "#FBCEB1FF", "苹果绿": "#8DB600FF", "暗金色": "#AA6C39FF", "玫红色": "#F52887FF",
    "绀紫色": "#4B0082FF", "紫罗兰": "#EE82EEFF", "草绿色": "#7CFC00FF", "青铜色": "#CD7F32FF",
    "玫紫色": "#9C27B0FF", "深棕色": "#654321FF", "深米色": "#E1C699FF", "墨绿色": "#004B23FF",
    "湖蓝色": "#008B8BFF", "拓竹绿": "#00A352FF", "浅灰色": "#D3D3D3FF", "暖黄色": "#FFDF00FF",
    "苹果绿色": "#8DB600FF", "南瓜橙色": "#FF7518FF", "桃红色": "#FF1493FF", "松石绿色": "#40E0D0FF",
    "钴蓝色": "#0047ABFF", "可可棕色": "#D2691EFF", "胭脂红色": "#BE0032FF", "圣诞绿": "#006400FF",
    "半透明": "#FFFFFF88", "香芋紫": "#D8BFD8FF", "桃红": "#FF1493FF", "柠檬黄": "#FFF44FFF",
    "珍珠白": "#F0EAD6FF", "骨白色": "#F9F6EEFF", "牛油果色": "#568203FF", "拿铁色": "#C5A059FF"
}

def get_filaments():
    req = urllib.request.Request(URL_BAMBU+"?limit=500", headers={"Authorization": "Bearer "+TOKEN, "Accept": "application/json", "User-Agent": "BBL-Slicer/1.9.0"})
    try:
        res = json.loads(urllib.request.urlopen(req).read().decode())
        return {f["id"]: f for f in res.get("hits", [])}
    except Exception as e:
        print("GET Error:", e)
        return {}

def post_filament(payload):
    req = urllib.request.Request(URL_BAMBU, method="POST", data=json.dumps(payload).encode("utf-8"), headers={
        "Authorization": "Bearer "+TOKEN, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "BBL-Slicer/1.9.0"
    })
    try:
        urllib.request.urlopen(req)
        return True
    except Exception as e:
        print(f"POST Error for {payload['filamentName']}:", e)
        if hasattr(e, "read"): print(e.read().decode())
        return False

print("Setting up database...")
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS spools (
    id TEXT PRIMARY KEY,
    color_id TEXT NOT NULL,
    bambu_cloud_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'opened',
    gross_weight_g REAL,
    empty_weight_g REAL,
    net_weight_g REAL NOT NULL,
    created_at TEXT NOT NULL
);
""")

c.execute("SELECT c.id, c.name, c.opened, c.unopened, p.brand, p.material, p.product_line FROM colors c JOIN products p ON c.product_id = p.id")
rows = c.fetchall()

print("Fetching initial Cloud filaments...")
cloud_filaments = get_filaments()
existing_ids = set(cloud_filaments.keys())

# Collect all items to push
to_push = []
for row in rows:
    color_id, color_name, opened, unopened, brand, material, p_line = row
    total = opened + unopened
    if total <= 0: continue
    
    # 1. Vendor mapping
    v = brand.lower()
    if v == "三绿" or v == "sunlu": vendor = "SUNLU"
    elif v == "拓竹" or v == "bambu lab" or v == "bambulab": vendor = "Bambu Lab"
    elif v == "polymaker": vendor = "Polymaker"
    else: vendor = "Generic"
    
    # 2. Material mapping
    m = material.upper()
    if "PLA" in m: f_type = "PLA"
    elif "PETG" in m: f_type = "PETG"
    elif "ABS" in m: f_type = "ABS"
    elif "ASA" in m: f_type = "ASA"
    elif "TPU" in m: f_type = "TPU"
    else: f_type = "PLA" # default fallback
    
    # 3. Name mapping
    if vendor == "Generic":
        name = f"{brand} {material} {p_line}".strip()
    else:
        name = f"{material} {p_line}".strip()
    
    # 4. Color mapping
    hex_color = COLORS.get(color_name, "#808080FF")
    
    for i in range(total):
        status = "opened" if i < opened else "unopened"
        payload = {
            "createType": "manual", "filamentVendor": vendor, "filamentType": f_type, 
            "filamentName": name, "filamentId": "", "isSupport": False, 
            "color": hex_color, "colorType": 2, "colors": [hex_color], 
            "trayIdName": "", "rolls": 1, "netWeight": 1000, "totalNetWeight": 1000, 
            "note": f"{color_name} - PrintPilot Sync", "inPrinter": False
        }
        to_push.append({"payload": payload, "color_id": color_id, "status": status})

print(f"Total spools to push: {len(to_push)}")

c.execute("SELECT COUNT(*) FROM spools")
spools_count = c.fetchone()[0]
if spools_count > 0:
    print(f"Found {spools_count} spools already in DB. Skipping push to avoid duplicates.")
    to_push = []

for item in to_push:
    payload = item["payload"]
    print(f"Pushing: {payload['filamentVendor']} {payload['filamentName']} ({payload['note']})")
    if post_filament(payload):
        time.sleep(1) # wait for bambu DB to settle
        new_fils = get_filaments()
        new_ids = set(new_fils.keys())
        diff = new_ids - existing_ids
        if len(diff) == 1:
            cloud_id = list(diff)[0]
            existing_ids.add(cloud_id)
            c.execute("INSERT INTO spools (id, color_id, bambu_cloud_id, status, net_weight_g, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), item["color_id"], cloud_id, item["status"], 1000.0, str(int(time.time())))
            )
            conn.commit()
            print(f"  -> Success! Cloud ID: {cloud_id}")
        else:
            print("  -> Could not uniquely identify new Cloud ID! Diff:", diff)
            existing_ids = new_ids # sync up anyway
    else:
        print("  -> Failed to push.")

conn.close()
print("Migration completed!")
