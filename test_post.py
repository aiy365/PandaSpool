
import json, urllib.request

url = "https://api.bambulab.cn/v1/design-user-service/my/filament/v2"
token = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"

payload = {
    "createType": "manual", 
    "filamentVendor": "Polymaker", 
    "filamentType": "ASA", 
    "filamentName": "PolyLite ASA", 
    "filamentId": "", 
    "isSupport": False, 
    "color": "#1F1F1F", 
    "colorType": 2, 
    "colors": [ "#1F1F1F" ], 
    "trayIdName": "", 
    "rolls": 1, 
    "netWeight": 1000, 
    "totalNetWeight": 1000, 
    "note": "PrintPilot Test", 
    "inPrinter": False
}

req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={
    "Authorization": "Bearer " + token, 
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "BBL-Slicer/1.9.0"
})

try:
    res = urllib.request.urlopen(req).read().decode()
    print("POST Response:", res)
except Exception as e:
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        print("Error HTTP", e.code, e.read().decode())
    else:
        print("Error:", e)

