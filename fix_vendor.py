import re

with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    js = f.read()

old_logic = """name := f.FilamentName
            if name == "" {
                name = f.FilamentID
            }
			presetMap[f.FilamentID] = Preset{ID: f.FilamentID, Name: name}"""
new_logic = """name := f.FilamentName
            if name == "" {
                name = f.FilamentID
            }
			presetMap[f.FilamentID] = Preset{ID: f.FilamentID, Name: f.FilamentVendor + " " + name}"""

js = js.replace(old_logic, new_logic)

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(js)
