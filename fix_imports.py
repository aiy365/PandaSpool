
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\"crypto/sha256\"", "")
text = text.replace("\"encoding/hex\"", "")
text = text.replace("\"errors\"", "")
text = text.replace("\"io/fs\"", "")
text = text.replace("\"os\"", "")
text = text.replace("\"log\"", "")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()
text = text.replace("\"strings\"\\n", "")
with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

