
import re
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

old_json = """	ezStatus := s.ez.Status()
	ezStatus["rotation"] = cfg.Ezviz.Rotation
	json.NewEncoder(w).Encode(map[string]any{"""

new_json = """	ezStatus := s.ez.Status()
	ezStatus["rotation"] = cfg.Ezviz.Rotation
	ezStatus["crop"] = cfg.Ezviz.Crop
	json.NewEncoder(w).Encode(map[string]any{"""

text = text.replace(old_json, new_json)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text)

