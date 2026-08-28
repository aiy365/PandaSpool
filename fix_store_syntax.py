import re

with open('internal/store/store.go', 'r', encoding='utf-8') as f:
    content = f.read()

broken = """	if err := s.migrateSpools()
	_, _ = s.DB.Exec("ALTER TABLE products ADD COLUMN bambu_preset_id TEXT NOT NULL DEFAULT ''"); err != nil {
		return nil, err
	}"""
fixed = """	if err := s.migrateSpools(); err != nil {
		return nil, err
	}
	_, _ = s.DB.Exec("ALTER TABLE products ADD COLUMN bambu_preset_id TEXT NOT NULL DEFAULT ''")
"""
content = content.replace(broken, fixed)

with open('internal/store/store.go', 'w', encoding='utf-8') as f:
    f.write(content)
print("Fixed Go syntax in store.go")
