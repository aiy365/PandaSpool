
import re
with open("internal/bambu/bambu.go", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """	merge("gcode_state", print["gcode_state"])
	merge("subtask", first(print, "subtask_name", "task_name", "gcode_file"))"""

new_code = """	merge("gcode_state", print["gcode_state"])
	merge("subtask", first(print, "subtask_name", "task_name", "gcode_file"))
	if vt, ok := print["vt_tray"].(map[string]any); ok {
		merge("vt_tray", vt)
	}
	if ams, ok := print["ams"].(map[string]any); ok {
		merge("ams", ams)
	}
	if tn := first(print, "tray_now", "ams_tray_now"); tn != nil {
		merge("tray_now", tn)
	}"""

text = text.replace(old_code, new_code)
with open("internal/bambu/bambu.go", "w", encoding="utf-8") as f:
    f.write(text)

