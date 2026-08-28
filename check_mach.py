
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("async function viewMachine(")
    print(text[idx:idx+1500])

