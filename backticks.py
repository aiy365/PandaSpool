
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

count = 0
for i, line in enumerate(text.split("\n")):
    if "`" in line:
        count += line.count("`")
        print(f"{i+1}: {line} ({count})")

