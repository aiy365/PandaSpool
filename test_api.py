
import json, urllib.request, ssl
ctx = ssl._create_unverified_context()
req = urllib.request.urlopen("https://3d.bstccc.cn/api/products", context=ctx)
data = json.loads(req.read())
print(len(data))

