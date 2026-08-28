
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, line in enumerate(lines):
    if "settings" in line and "hash" in line:
        print(line.strip())

