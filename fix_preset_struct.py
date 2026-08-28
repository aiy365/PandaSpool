import re

with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    js = f.read()

old_struct = """type Preset struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}"""
new_struct = """type Preset struct {
		ID       string `json:"id"`
		Name     string `json:"name"`
		Vendor   string `json:"vendor"`
		Material string `json:"material"`
	}"""
js = js.replace(old_struct, new_struct)

old_map = """presetMap[f.FilamentID] = Preset{ID: f.FilamentID, Name: f.FilamentVendor + " " + name}"""
new_map = """presetMap[f.FilamentID] = Preset{
				ID:       f.FilamentID,
				Name:     f.FilamentVendor + " " + name,
				Vendor:   f.FilamentVendor,
				Material: f.Category,
			}"""
js = js.replace(old_map, new_map)

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(js)
