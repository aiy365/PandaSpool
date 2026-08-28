import json, urllib.request

url = "https://api.bambulab.cn/v1/design-user-service/filament/config"
token = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"
req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token, "Accept": "application/json", "User-Agent": "BBL-Slicer/1.9.0"})
try:
    res = urllib.request.urlopen(req).read().decode()
    data = json.loads(res)
    for f in data["filamentSettings"]:
        if f["filamentVendor"] in ["Generic", "Polymaker", "SUNLU", "Bambu Lab"]:
            if f["filamentType"] in ["PLA", "PETG"]:
                print(f"{f['filamentVendor']} | {f['filamentType']} | {f['filamentName']} -> ID: {f['filamentId']}")
except Exception as e:
    print("Error:", e)
