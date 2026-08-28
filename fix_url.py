
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\"url\":         picUrl,", "\"url\":         \"https://3d.bstccc.cn/#/machine\",")

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

