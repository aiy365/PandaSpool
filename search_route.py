
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    for line in f:
        if "materials/" in line:
            print(line.strip())

