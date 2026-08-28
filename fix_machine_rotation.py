
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

old_json = """	json.NewEncoder(w).Encode(map[string]any{
		"bambu":    bambuStatus,
		"printing": s.bambu.HasPrintState(),
		"air":      airMap,
		"ezviz":    s.ez.Status(),
	})"""

new_json = """	ezStatus := s.ez.Status()
	ezStatus["rotation"] = cfg.Ezviz.Rotation
	json.NewEncoder(w).Encode(map[string]any{
		"bambu":    bambuStatus,
		"printing": s.bambu.HasPrintState(),
		"air":      airMap,
		"ezviz":    ezStatus,
	})"""

text = text.replace(old_json, new_json)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

