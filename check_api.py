
import json, urllib.request, ssl
ctx = ssl._create_unverified_context()
req = urllib.request.urlopen("https://3d.bstccc.cn/api/products/cb2f24e169f3e4fcec0159d60465fc63", context=ctx)
print(req.read().decode("utf-8"))

