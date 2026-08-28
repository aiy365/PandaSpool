import json, urllib.request

URL_BAMBU = "https://api.bambulab.cn/v1/design-user-service/my/filament/v2"
TOKEN = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"

# Our official ID mapping
ID_MAP = {
    "Bambu Lab_PLA": "GFA00",
    "Bambu Lab_PETG": "GFG00",
    "Generic_PLA": "GFL99",
    "Generic_PETG": "GFG99",
    "Polymaker_PLA": "GFL00",
    "Polymaker_PETG": "GFG60",
    "SUNLU_PLA": "GFSNL03",  # default PLA+
    "SUNLU_PETG": "GFSNL08"
}

def get_filaments():
    req = urllib.request.Request(URL_BAMBU+"?limit=500", headers={"Authorization": "Bearer "+TOKEN, "Accept": "application/json", "User-Agent": "BBL-Slicer/1.9.0"})
    res = json.loads(urllib.request.urlopen(req).read().decode())
    return res.get("hits", [])

def patch_filament(f, new_id):
    f["filamentId"] = new_id
    req = urllib.request.Request(URL_BAMBU, method="PUT", data=json.dumps(f).encode("utf-8"), headers={
        "Authorization": "Bearer "+TOKEN, "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "BBL-Slicer/1.9.0"
    })
    urllib.request.urlopen(req)

fils = get_filaments()
count = 0
for f in fils:
    # Only patch if missing or we want to ensure it has a valid one
    if not f.get("filamentId"):
        vendor = f.get("filamentVendor", "Generic")
        ftype = f.get("filamentType", "PLA")
        
        # specific fixes for sub-types
        if vendor == "SUNLU" and "PLA+ 2.0" in f.get("filamentName", ""):
            new_id = "GFSNL04"
        elif vendor == "SUNLU" and "Matte" in f.get("filamentName", ""):
            new_id = "GFSNL02"
        elif vendor == "Generic" and "HF" in f.get("filamentName", "") and ftype == "PETG":
            new_id = "GFG96"
        elif vendor == "Generic" and "High Speed" in f.get("filamentName", ""):
            new_id = "GFL95"
        else:
            new_id = ID_MAP.get(f"{vendor}_{ftype}", ID_MAP.get(f"Generic_{ftype}", "GFL99"))
            
        print(f"Patching {vendor} {f.get('filamentName')} -> {new_id}")
        patch_filament(f, new_id)
        count += 1

print(f"Patched {count} filaments successfully!")
