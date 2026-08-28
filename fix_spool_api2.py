import re
with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    js = f.read()

old_fil = "filamentID := getBambuFilamentID(targetProduct.Material)"
new_fil = """filamentID := targetProduct.BambuPresetID
	if filamentID == "" {
		filamentID = getBambuFilamentID(targetProduct.Material)
	}"""
js = js.replace(old_fil, new_fil)

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(js)
