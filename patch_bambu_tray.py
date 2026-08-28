
import re
with open("internal/bambu/bambu.go", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """	if ams, ok := print["ams"].(map[string]any); ok {
		merge("ams", ams)
	}
	if tn := first(print, "tray_now", "ams_tray_now"); tn != nil {
		merge("tray_now", tn)
	}"""

new_code = """	if ams, ok := print["ams"].(map[string]any); ok {
		merge("ams", ams)
		if tn := first(ams, "tray_now"); tn != nil {
			merge("tray_now", tn)
		}
	}
	if tn := first(print, "tray_now", "ams_tray_now"); tn != nil {
		merge("tray_now", tn)
	}"""

text = text.replace(old_code, new_code)
with open("internal/bambu/bambu.go", "w", encoding="utf-8") as f:
    f.write(text)

