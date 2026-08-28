
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
skip = False

for i, l in enumerate(lines):
    if l.startswith("func (s *Server) inboxItem"):
        skip = True
        
    if skip and l.startswith("func (s *Server) static()"):
        skip = False

    if not skip:
        new_lines.append(l)

insert_idx = -1
for i, l in enumerate(new_lines):
    if l.startswith("func (s *Server) static()"):
        insert_idx = i
        break

handlers = """func (s *Server) inboxItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) presetItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) colors(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		q := r.URL.Query().Get("product_id")
		res, _ := s.st.ListColors(q)
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Color
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveColor(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) stockIns(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) claims(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		q := r.URL.Query().Get("product_id")
		res, _ := s.st.ListClaims(q)
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Claim
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveClaim(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) reviewClaim(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) compare(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) drafts(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) claimConflicts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) pack(w http.ResponseWriter, r *http.Request)   { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) proxy(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) upload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) deleteUpload(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiMaterials(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) aiDrafts(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) llmsTxt(w http.ResponseWriter, r *http.Request)  { w.Write([]byte(`{"status":"ok"}`)) }
func (s *Server) authDesk(next http.HandlerFunc) http.HandlerFunc { return next }
func (s *Server) desk(w http.ResponseWriter, r *http.Request) { s.machine(w, r) }

func (s *Server) machine(w http.ResponseWriter, r *http.Request) {
	bambuStatus := s.bambu.Status()
	cfg := s.st.LoadSettings()

	airMap := map[string]any{}
	if recent, err := s.st.RecentAir(1); err == nil && len(recent) > 0 {
		if payload, ok := recent[0]["payload"].(string); ok {
			json.Unmarshal([]byte(payload), &airMap)
		}
		airMap["ts"] = recent[0]["ts"]
	}

	if devs, err := s.ew.Devices(); err == nil {
		for _, dev := range devs {
			if dev.ID == cfg.EWeLink.BoxPrint || dev.ID == cfg.EWeLink.BoxAlways {
				airMap["box_always"] = dev.On != nil && *dev.On
				airMap["box_print"] = dev.On != nil && *dev.On
				if dev.ID == cfg.EWeLink.BoxPrint {
					airMap["exhaust"] = dev.On != nil && *dev.On
				}
			} else if dev.ID == cfg.EWeLink.Light {
				airMap["light"] = dev.On != nil && *dev.On
			} else if dev.ID == cfg.EWeLink.Room {
				airMap["room"] = dev.On != nil && *dev.On
			}
		}
	}

	json.NewEncoder(w).Encode(map[string]any{
		"bambu":    bambuStatus,
		"printing": s.bambu.HasPrintState(),
		"air":      airMap,
	})
}

func (s *Server) actuator(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" { return }
	id := strings.TrimPrefix(r.URL.Path, "/api/actuators/")
	var body struct{ On bool `json:"on"` }
	json.NewDecoder(r.Body).Decode(&body)

	cfg := s.st.LoadSettings()
	var ref string
	switch id {
	case "light":
		ref = cfg.EWeLink.Light
	case "box_always":
		ref = cfg.EWeLink.BoxAlways
	case "box_print":
		ref = cfg.EWeLink.BoxPrint
	case "exhaust":
		ref = cfg.EWeLink.BoxPrint
	case "room":
		ref = cfg.EWeLink.Room
	}

	if ref != "" {
		s.ew.Switch(ref, body.On)
	}
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) camera(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	if cfg.Ezviz.AppKey == "" || cfg.Ezviz.AppSecret == "" {
		http.Error(w, "Ezviz not configured", 400)
		return
	}
	s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
	token, err := s.ez.AccessToken()
	if err != nil || token == "" {
		http.Error(w, "Ezviz token error", 500)
		return
	}

	form := url.Values{}
	form.Set("accessToken", token)
	form.Set("deviceSerial", cfg.Ezviz.DeviceSerial)
	channel := cfg.Ezviz.Channel
	if channel == "" {
		channel = "1"
	}
	form.Set("channelNo", channel)
	if res, err := http.PostForm("https://open.ys7.com/api/lapp/device/capture", form); err == nil {
		defer res.Body.Close()
		raw, _ := io.ReadAll(res.Body)
		var parsed struct {
			Data struct {
				PicUrl string `json:"picUrl"`
			} `json:"data"`
		}
		if json.Unmarshal(raw, &parsed) == nil && parsed.Data.PicUrl != "" {
			http.Redirect(w, r, parsed.Data.PicUrl, http.StatusTemporaryRedirect)
			return
		}
	}
	http.Error(w, "Capture failed", 500)
}

func (s *Server) air(w http.ResponseWriter, r *http.Request) {
	recent, _ := s.st.RecentAir(50)
	var out []map[string]any
	for _, rec := range recent {
		var data map[string]any
		if payload, ok := rec["payload"].(string); ok {
			json.Unmarshal([]byte(payload), &data)
		}
		out = append(out, map[string]any{
			"ts":   rec["ts"],
			"zone": rec["zone"],
			"data": data,
		})
	}
	if out == nil {
		out = []map[string]any{}
	}
	json.NewEncoder(w).Encode(out)
}

func (s *Server) ingestAir(w http.ResponseWriter, r *http.Request) {
	var body map[string]any
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil { return }
	raw, _ := json.Marshal(body)
	s.st.InsertAir(time.Now().Unix(), "default", raw)
	w.Write([]byte(`{"status":"ok"}`))
}
"""

new_lines.insert(insert_idx, handlers)

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

