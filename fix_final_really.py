
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("w.Write([]byte(`{\"status\":\"ok\"", "w.Write([]byte(\"{\\\"status\\\":\\\"ok\\\"}\"))}")

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

