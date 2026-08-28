
with open("test_app.js", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("async function boot()")
print(text[idx:idx+500])

