
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("const draw = async () => {")
    print(text[idx+1500:idx+3000])

