package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"pandaspool/internal/bambu"
	"pandaspool/internal/store"
	"regexp"
	"strings"
	"time"
)

func (s *Server) spoolsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		s.spoolsList(w, r)
		return
	}
	if r.Method == http.MethodPost {
		jsonError(w, "拓竹云只读模式：请在拓竹 Studio 或 Bambu Handy App 中建档", http.StatusBadRequest)
		return
	}
	http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
}

func (s *Server) spoolItemHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/spools/")
	parts := strings.Split(path, "/")
	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	id := parts[0]

	if len(parts) == 2 {
		if parts[1] == "weight" && r.Method == http.MethodPut {
			s.spoolUpdateWeight(w, r, id)
			return
		}
		if parts[1] == "status" && r.Method == http.MethodPut {
			s.spoolUpdateStatus(w, r, id)
			return
		}
	}

	if len(parts) == 1 && r.Method == http.MethodDelete {
		s.spoolDelete(w, r, id)
		return
	}

	http.Error(w, "not found", http.StatusNotFound)
}

func (s *Server) spoolsList(w http.ResponseWriter, r *http.Request) {
	spools, err := s.st.ListSpools()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(spools)
}

func (s *Server) cloudAdapter() (*bambu.CloudAdapter, error) {
	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		return nil, fmt.Errorf("未配置拓竹云 token，请先到设置页登录拓竹")
	}
	return bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken), nil
}

// spoolNoteRe 从云端备注里提取 PandaSpool 短编号（如 pm001）。
// 备注格式：<编号> <颜色> <站点名>（历史格式 "PandaSpool <编号> <颜色>" 同样命中）。
var spoolNoteRe = regexp.MustCompile(`(?i)\b([a-z]{1,3}\d{3,4})\b`)

func SpoolCodeFromNote(note string) string {
	if m := spoolNoteRe.FindStringSubmatch(note); m != nil {
		return strings.ToLower(m[1])
	}
	return ""
}

// spoolCloudSync 从拓竹云全量拉取耗材并同步至本地 spools 表（只读同步，绝不向云端写入）
func (s *Server) spoolCloudSync(w http.ResponseWriter, r *http.Request) {
	ad, err := s.cloudAdapter()
	if err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}
	filaments, err := ad.ListFilaments()
	if err != nil {
		jsonError(w, err.Error(), http.StatusBadGateway)
		return
	}
	existing, err := s.st.ListSpools()
	if err != nil {
		jsonError(w, err.Error(), http.StatusInternalServerError)
		return
	}
	byCloudID := make(map[int64]store.Spool)
	for _, sp := range existing {
		if sp.BambuCloudID > 0 {
			byCloudID[sp.BambuCloudID] = sp
		}
	}
	now := time.Now().UTC().Format(time.RFC3339)
	syncedCount := 0
	for _, f := range filaments {
		if f.ID <= 0 {
			continue
		}
		colorHex := strings.TrimPrefix(f.Color, "#")
		if len(colorHex) >= 6 {
			colorHex = colorHex[:6]
		}
		name := f.FilamentName
		if name == "" {
			name = f.FilamentID
		}
		vendor := vendorOf(&f)
		netW := float64(f.NetWeight)
		if netW <= 0 {
			netW = float64(f.TotalNetWeight)
		}
		if netW <= 0 {
			netW = 1000
		}

		if sp, ok := byCloudID[f.ID]; ok {
			sp.BambuVendor = vendor
			sp.BambuFilamentName = name
			sp.BambuFilamentID = f.FilamentID
			sp.ColorHex = colorHex
			sp.NetWeightG = netW
			sp.LastSyncedAt = now
			if _, err := s.st.SaveSpool(sp); err == nil {
				syncedCount++
			}
		} else {
			code := SpoolCodeFromNote(f.Note)
			if code == "" {
				code, _ = s.st.NextShortCode("PP-")
			}
			newSpool := store.Spool{
				ShortCode:         strings.ToUpper(code),
				BambuCloudID:      f.ID,
				BambuVendor:       vendor,
				BambuFilamentName: name,
				BambuFilamentID:   f.FilamentID,
				ColorHex:          colorHex,
				NetWeightG:        netW,
				Status:            "opened",
				SyncEnabled:       true,
				LastSyncedAt:      now,
			}
			if _, err := s.st.SaveSpool(newSpool); err == nil {
				syncedCount++
			}
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "count": syncedCount})
}

func vendorOf(f *bambu.CloudFilament) string {
	if v := strings.TrimSpace(f.FilamentVendor); v != "" {
		return v
	}
	name := strings.TrimSpace(f.FilamentName)
	if i := strings.IndexAny(name, " \t"); i > 0 {
		return name[:i]
	}
	return name
}

func jsonError(w http.ResponseWriter, msg string, code int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(code)
	json.NewEncoder(w).Encode(map[string]any{"error": msg})
}

func jsonOK(w http.ResponseWriter) {
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"ok":true}`))
}

func (s *Server) spoolUpdateWeight(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		NetWeightG float64 `json:"net_weight_g"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	sp, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	if sp.BambuCloudID > 0 {
		if ad, err := s.cloudAdapter(); err == nil {
			_ = ad.UpdateWeight(sp.BambuCloudID, sp.BambuFilamentName, int(req.NetWeightG))
		}
	}

	err = s.st.UpdateSpoolWeight(id, req.NetWeightG)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) spoolUpdateStatus(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		Status string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	sp, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	if req.Status == "depleted" && sp.BambuCloudID > 0 {
		if ad, err := s.cloudAdapter(); err == nil {
			_ = ad.DeleteFilaments([]int64{sp.BambuCloudID})
		}
	}

	err = s.st.SetSpoolStatus(id, req.Status)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) spoolDelete(w http.ResponseWriter, r *http.Request, id string) {
	sp, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	if sp.BambuCloudID > 0 {
		if ad, err := s.cloudAdapter(); err == nil {
			_ = ad.DeleteFilaments([]int64{sp.BambuCloudID})
		}
	}

	err = s.st.DeleteSpool(id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

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
		ID       string `json:"id"`
		Name     string `json:"name"`
		Vendor   string `json:"vendor"`
		Material string `json:"material"`
	}
	presetMap := make(map[string]Preset)
	for _, f := range filaments {
		if f.FilamentID != "" {
            name := f.FilamentName
            if name == "" {
                name = f.FilamentID
            }
			presetMap[f.FilamentID] = Preset{
				ID:       f.FilamentID,
				Name:     f.FilamentVendor + " " + name,
				Vendor:   f.FilamentVendor,
				Material: f.Category,
			}
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

// spoolCloudHandler 路由：/api/spools/cloud/sync
func (s *Server) spoolCloudHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/spools/cloud/")
	if r.Method == http.MethodPost && path == "sync" {
		s.spoolCloudSync(w, r)
		return
	}
	http.Error(w, "not found", http.StatusNotFound)
}

// spoolSyncColor 按颜色台账补齐（只读模式下关闭）
func (s *Server) spoolSyncColor(w http.ResponseWriter, r *http.Request) {
	jsonError(w, "拓竹云只读模式：不支持向拓竹云建档", http.StatusBadRequest)
}
