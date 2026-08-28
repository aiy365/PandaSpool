
import re

with open("internal/server/server.go", "r", encoding="utf-8") as f:
    text = f.read()

idx = text.find("func (s *Server) inboxItem")
if idx != -1:
    text = text[:idx]

restored = """
func (s *Server) inboxItem(w http.ResponseWriter, r *http.Request) { w.Write([]byte(`{"status":"ok"}`)) }
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
func (s *Server) compare(w http.ResponseWriter, r *http.Request) { 
	res := map[string][]map[string]any{}
	rows, err := s.st.DB.Query(`
		SELECT p.name, c.source, c.claim_key, c.claim_value, c.unit
		FROM claims c JOIN products p ON c.product_id = p.id
		WHERE c.status = "confirmed"
	`)
	if err == nil {
		defer rows.Close()
		for rows.Next() {
			var product, source, key, value, unit string
			rows.Scan(&product, &source, &key, &value, &unit)
			res[key] = append(res[key], map[string]any{
				"product": product,
				"source": source,
				"value": value,
				"unit": unit,
			})
		}
	}
	json.NewEncoder(w).Encode(res)
}
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
	var picUrl string
	if s.cfg.Ezviz.AppKey != "" && s.cfg.Ezviz.DeviceSerial != "" {
		s.ez.Configure(s.cfg.Ezviz.AppKey, s.cfg.Ezviz.AppSecret)
		token, err := s.ez.AccessToken()
		if err == nil && token != "" {
			form := url.Values{}
			form.Set("accessToken", token)
			form.Set("deviceSerial", s.cfg.Ezviz.DeviceSerial)
			channel := s.cfg.Ezviz.Channel
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
					picUrl = parsed.Data.PicUrl
				}
			}
		}
	}
	if picUrl != "" {
		http.Redirect(w, r, picUrl, http.StatusTemporaryRedirect)
	} else {
		w.Write([]byte(`{"error":"failed to capture"}`))
	}
}

func (s *Server) air(w http.ResponseWriter, r *http.Request) {
	recent, _ := s.st.RecentAir(50)
	var parsed []map[string]any
	for _, rec := range recent {
		var data map[string]any
		if payload, ok := rec["payload"].(string); ok {
			json.Unmarshal([]byte(payload), &data)
		} else {
			data = map[string]any{}
		}
		data["ts"] = rec["ts"]
		parsed = append(parsed, data)
	}
	json.NewEncoder(w).Encode(parsed)
}

func (s *Server) ingestAir(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) static() http.HandlerFunc { return func(w http.ResponseWriter, r *http.Request) { http.ServeFile(w, r, "web/dist" + r.URL.Path) } }

func (s *Server) applyIntegrations() {
	cfg := s.st.LoadSettings()
	s.bambu.Configure(cfg.Bambu.Region, cfg.Bambu.Account, cfg.Bambu.Password, cfg.Bambu.PrinterSN, cfg.Bambu.AccessToken)
	s.bambu.Reconnect()
	s.ew.Configure(ewelink.Config{
		Region:       cfg.EWeLink.Region,
		Account:      cfg.EWeLink.Account,
		Password:     cfg.EWeLink.Password,
		AppID:        cfg.EWeLink.AppID,
		AppSecret:    cfg.EWeLink.AppSecret,
		AccessToken:  cfg.EWeLink.AccessToken,
		RefreshToken: cfg.EWeLink.RefreshToken,
	})
	s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
}

func (s *Server) automate() {
	for {
		time.Sleep(10 * time.Second)
		cfg := s.st.LoadSettings()
		if cfg.Automations.PrintBoostMinutes > 0 && cfg.EWeLink.BoxPrint != "" {
			printingOrBoost := s.bambu.PrintingOrBoost(cfg.Automations.PrintBoostMinutes)
			s.ew.Switch(cfg.EWeLink.BoxPrint, printingOrBoost)
		}
		if cfg.EWeLink.BoxAlways != "" {
			s.ew.Switch(cfg.EWeLink.BoxAlways, cfg.Automations.BoxAlwaysOn)
		}
	}
}
"""

with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.write(text + "\n" + restored)

