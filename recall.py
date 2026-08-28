
import urllib.request
import json
wcCorp = "ww2a73e45de188fa04"
wcSec = "3jEHnUDieOkXRQn5lOHjryiU2BnMG0KMHhx70oLV0Ig"

token_url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={wcCorp}&corpsecret={wcSec}"
res = json.loads(urllib.request.urlopen(urllib.request.Request(token_url)).read().decode())
token = res.get("access_token", "")

url = "https://qyapi.weixin.qq.com/cgi-bin/message/recall?access_token=" + token
data = json.dumps({"msgid": "SvpFVDN5j3cfoDnUMZjZA7SYbT8KvBfePW8jqI8AVh57dKBfZSy6zY3S7tBhzxFEqfeZZbenqG-vP8O1EdYangyiIn4P3ja-mRSeXdoCtx9CCb9_FDVw_ToEORvEfXOf"}).encode()
req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
print(urllib.request.urlopen(req).read().decode())

