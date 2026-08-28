
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

count = 0
for i, line in enumerate(text.split("\n")):
    count += line.count("`")
    if count % 2 != 0:
        print(f"Line {i+1}: {line}")

