
import re
with open("internal/server/notify.go", "r", encoding="utf-8") as f:
    text = f.read()

# Replace: endedAt, _ := st["print_ended_at"].(time.Time)
# With:
# var endedAt time.Time
# if endStr, ok := st["print_ended_at"].(string); ok && endStr != "" {
#     endedAt, _ = time.Parse(time.RFC3339, endStr)
# }

old = "endedAt, _ := st[\"print_ended_at\"].(time.Time)"
new = """var endedAt time.Time
	if endStr, ok := st["print_ended_at"].(string); ok && endStr != "" {
		endedAt, _ = time.Parse(time.RFC3339, endStr)
	}"""
text = text.replace(old, new)

with open("internal/server/notify.go", "w", encoding="utf-8") as f:
    f.write(text)

