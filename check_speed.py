
import re
with open("internal/bambu/bambu.go", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """	merge("remaining", first(print, "mc_remaining_time", "remain_time"))
	if st := first(print, "mc_print_stage", "print_stage"); st != nil {
		merge("stage", stageName(st))
	}"""

new_code = """	merge("remaining", first(print, "mc_remaining_time", "remain_time"))
	merge("spd_mag", first(print, "spd_mag"))
	merge("spd_lvl", first(print, "spd_lvl"))
	merge("fan_gear", first(print, "cooling_fan_speed"))
	if st := first(print, "mc_print_stage", "print_stage"); st != nil {
		merge("stage", stageName(st))
	}"""

text = text.replace(old_code, new_code)
with open("internal/bambu/bambu.go", "w", encoding="utf-8") as f:
    f.write(text)

