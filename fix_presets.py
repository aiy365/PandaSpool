import re

with open('internal/server/server.go', 'r', encoding='utf-8') as f:
    content = f.read()

if '"/api/presets/sync"' not in content:
    content = content.replace('mux.HandleFunc("/api/spools/", s.auth(s.spoolItemHandler))',
                              'mux.HandleFunc("/api/spools/", s.auth(s.spoolItemHandler))\n\tmux.HandleFunc("/api/presets", s.auth(s.presetsListHandler))\n\tmux.HandleFunc("/api/presets/sync", s.auth(s.presetsSyncHandler))')

with open('internal/server/server.go', 'w', encoding='utf-8') as f:
    f.write(content)

with open('internal/server/spool_api.go', 'r', encoding='utf-8') as f:
    content = f.read()

presets_logic = """
func (s *Server) presetsListHandler(w http.ResponseWriter, r *http.Request) {
	val, _ := s.st.GetMeta("bambu_presets")
	if val == "" {
		val = "[]"
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(val))
}

func (s *Server) presetsSyncHandler(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		http.Error(w, "bambu token not configured", http.StatusBadRequest)
		return
	}

	adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
	filaments, err := adapter.ListFilaments()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	type Preset struct {
		ID   string `json:"id"`
		Name string `json:"name"`
	}
	presetMap := make(map[string]Preset)
	for _, f := range filaments {
		if f.FilamentID != "" {
            name := f.FilamentName
            if name == "" {
                name = f.FilamentID
            }
			presetMap[f.FilamentID] = Preset{ID: f.FilamentID, Name: name}
		}
	}
	
	var out []Preset
	for _, p := range presetMap {
		out = append(out, p)
	}
	
	b, _ := json.Marshal(out)
	s.st.SetMeta("bambu_presets", string(b))
	
	w.Header().Set("Content-Type", "application/json")
	w.Write(b)
}
"""

if "func (s *Server) presetsSyncHandler" not in content:
    content += presets_logic

with open('internal/server/spool_api.go', 'w', encoding='utf-8') as f:
    f.write(content)
print("Updated internal/server/server.go and spool_api.go for Presets Sync")
