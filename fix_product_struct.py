import re
with open('internal/store/store.go', 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'Material\s+string\s+`json:"material"`', 'Material    string            `json:"material"`\n\tBambuPresetID string            `json:"bambu_preset_id"`', content)

with open('internal/store/store.go', 'w', encoding='utf-8') as f:
    f.write(content)
