import os
import glob

# Rename Go imports and module name
def replace_in_file(filepath, old_str, new_str):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if old_str in content:
        content = content.replace(old_str, new_str)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

go_files = glob.glob('**/*.go', recursive=True)
for f in go_files:
    replace_in_file(f, 'printpilot-hub/', 'pandaspool/')
    replace_in_file(f, 'PrintPilot', 'PandaSpool')

replace_in_file('go.mod', 'module printpilot-hub', 'module pandaspool')
replace_in_file('live_app.js', 'PrintPilot', 'PandaSpool')
replace_in_file('live_app.js', 'printpilot', 'pandaspool')
replace_in_file('web/dist/index.html', 'PrintPilot', 'PandaSpool')
replace_in_file('web/dist/styles.css', 'PrintPilot', 'PandaSpool')

# Rename cmd dir
if os.path.exists('cmd/printpilot'):
    os.rename('cmd/printpilot', 'cmd/pandaspool')
    print("Renamed cmd/printpilot to cmd/pandaspool")

print("Global rename complete.")
