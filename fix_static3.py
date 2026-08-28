
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("\\n", "\n").replace("\\t", "\t")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

