
import json, urllib.request

url = "https://api.bambulab.cn/v1/design-user-service/my/filament/v2?offset=0&limit=50"
token = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"
req = urllib.request.Request(url, headers={
    "Authorization": "Bearer " + token, 
    "Accept": "application/json",
    "User-Agent": "BBL-Slicer/1.9.0"
})

try:
    res = urllib.request.urlopen(req).read().decode()
    data = json.loads(res)
    print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        print("Error HTTP", e.code, e.read().decode())
    else:
        print("Error:", e)

