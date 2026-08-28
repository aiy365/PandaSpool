
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

# Replace all backticks inside mocked writes
text = text.replace("`{\"status\":\"ok\"}`", "\"{\\\"status\\\":\\\"ok\\\"}\"")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

