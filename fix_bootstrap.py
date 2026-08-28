import re

with open('internal/server/server.go', 'r', encoding='utf-8') as f:
    go_src = f.read()

old_boot = """w.Write([]byte(`{"ready":` + fmt.Sprintf("%v", s.st.HasAdmin()) + `}`))"""
new_boot = """cfg := s.st.LoadSettings()
	title := cfg.Site.Title
	if title == "" {
		title = "PandaSpool"
	}
	w.Write([]byte(`{"ready":` + fmt.Sprintf("%v", s.st.HasAdmin()) + `,"site":{"title":"` + title + `"}}`))"""
go_src = go_src.replace(old_boot, new_boot)

with open('internal/server/server.go', 'w', encoding='utf-8') as f:
    f.write(go_src)
