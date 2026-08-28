
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("try { s = await api(\"/api/settings\"); }")
print(text[max(0, idx-200):idx+500])

