
import json, urllib.request

url = "https://api.bambulab.cn/v1/design-user-service/my/filament/v2/batch"
token = "AQB9moijNyTk9F6TfFd_-WRSe6Jiug7Dk-FhVusQsBKXAkHbzAaOliR5milE9EiAPZ626WKUoKWqnMzysDGUabmToBMshFjGU0I9qFTy1V5V-KtzSLvQzLaWrhx28R1_Nht-Glvk_cUws6al"

# It might take a JSON array of IDs or an object like {"ids": [2922066]}
# Let us try a plain array first: [2922066]
payload = [2922066]

req = urllib.request.Request(url, method="DELETE", data=json.dumps(payload).encode("utf-8"), headers={
    "Authorization": "Bearer " + token, 
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "BBL-Slicer/1.9.0"
})

try:
    res = urllib.request.urlopen(req).read().decode()
    print("DELETE Response (Array):", res)
except Exception as e:
    import urllib.error
    if isinstance(e, urllib.error.HTTPError):
        print("Error HTTP Array", e.code, e.read().decode())
        
        # Try {"ids": [2922066]}
        payload2 = {"ids": [2922066]}
        req2 = urllib.request.Request(url, method="DELETE", data=json.dumps(payload2).encode("utf-8"), headers={
            "Authorization": "Bearer " + token, 
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "BBL-Slicer/1.9.0"
        })
        try:
            res2 = urllib.request.urlopen(req2).read().decode()
            print("DELETE Response (Object):", res2)
        except Exception as e2:
             if isinstance(e2, urllib.error.HTTPError):
                 print("Error HTTP Object", e2.code, e2.read().decode())
             else:
                 print("Error2:", e2)
    else:
        print("Error:", e)

