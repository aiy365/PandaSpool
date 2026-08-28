
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace(
"""	if err == nil {
		defer rows.Close()""",
"""	if err != nil {
		res["error"] = []map[string]any{{"value": err.Error()}}
	} else {
		defer rows.Close()"""
)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

