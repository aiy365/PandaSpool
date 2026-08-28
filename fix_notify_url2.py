
import re
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("""								"url":         func() string { if picUrl != "" { return picUrl } else { return "https://3d.bstccc.cn" } }(),""", """								"url":         picUrl,""")

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

