package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"pandaspool/internal/bambu"
	"pandaspool/internal/store"
	"strings"
	"github.com/mozillazg/go-pinyin"
)

func (s *Server) spoolsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		s.spoolsList(w, r)
		return
	}
	if r.Method == http.MethodPost {
		s.spoolIntake(w, r)
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

type intakeReq struct {
	ColorID  string `json:"color_id"`
	Quantity int    `json:"quantity"`
}


func getInitial(s string) string {
	s = strings.TrimSpace(s)
	if len(s) == 0 {
		return "x"
	}
	r := []rune(s)[0]
	if (r >= 'A' && r <= 'Z') || (r >= 'a' && r <= 'z') {
		return strings.ToLower(string(r))
	}
	dict := map[rune]string{
		'拓': "t", '竹': "z", '易': "y", '生': "s", '兰': "l", '博': "b", '创': "c", '想': "x", '闪': "s", '铸': "z",
		'红': "h", '粉': "f", '蓝': "l", '绿': "l", '黄': "h", '黑': "h", '白': "b", '紫': "z", '棕': "z", '透': "t",
		'金': "j", '银': "y", '灰': "h", '彩': "c", '特': "t", '橙': "c", '青': "q", '木': "m", '自': "z", '明': "m",
		'亚': "y", '哑': "y", '亮': "l", '丝': "s", '夜': "y", '大': "d", '筒': "t", '无': "w",
	}
	if val, ok := dict[r]; ok {
		return val
	}
	a := pinyin.NewArgs()
	a.Style = pinyin.FirstLetter
	py := pinyin.Pinyin(string(r), a)
	if len(py) > 0 && len(py[0]) > 0 {
		return strings.ToLower(py[0][0])
	}
	return "x"
}

func getBambuFilamentID(material string) string {
	m := strings.ToUpper(strings.TrimSpace(material))
	if strings.Contains(m, "PLA") {
		return "GFL99"
	}
	if strings.Contains(m, "PETG") {
		return "GFG99"
	}
	if strings.Contains(m, "ABS") {
		return "GFB99"
	}
	if strings.Contains(m, "TPU") {
		return "GFU99"
	}
	return "GFL99"
}

// colorHexFromName 把商家颜色名近似成十六进制色（RRGGBB），与拓竹云端
// 耗材颜色对齐；认不出的给中灰。
func colorHexFromName(name string) string {
	n := name
	rules := []struct {
		key string
		hex string
	}{
		{"黑", "171717"}, {"深灰", "52525b"}, {"浅灰", "d4d4d8"}, {"灰", "71717a"}, {"银", "c0c0c0"},
		{"白", "ffffff"},
		{"酒红", "be123c"}, {"玫红", "d946ef"}, {"粉", "f472b6"}, {"红", "ef4444"},
		{"橙", "f97316"},
		{"金黄", "d4a017"}, {"黄", "eab308"}, {"金", "daa520"},
		{"墨绿", "166534"}, {"嫩绿", "86efac"}, {"浅绿", "86efac"}, {"深绿", "166534"}, {"绿", "22c55e"},
		{"青", "06b6d4"},
		{"天蓝", "38bdf8"}, {"浅蓝", "38bdf8"}, {"深蓝", "1d4ed8"}, {"蓝", "3b82f6"},
		{"深紫", "581c87"}, {"紫", "a855f7"},
		{"棕", "78350f"}, {"木", "78350f"}, {"咖", "6f4e37"},
		{"透明", "e0f2fe"}, {"自然", "e0f2fe"}, {"骨", "fef3c7"}, {"米", "fef3c7"}, {"肤", "fef3c7"},
	}
	for _, r := range rules {
		if strings.Contains(n, r.key) {
			return r.hex
		}
	}
	return "a0a0a0"
}

func (s *Server) spoolIntake(w http.ResponseWriter, r *http.Request) {
	var req intakeReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	var targetColor *store.Color
	var targetProduct *store.Product
	prods, err := s.st.ListProducts()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	for _, p := range prods {
		for _, c := range p.Colors {
			if c.ID == req.ColorID {
				tc := c
				tp := p
				targetColor = &tc
				targetProduct = &tp
				break
			}
		}
		if targetColor != nil {
			break
		}
	}

	if targetColor == nil || targetProduct == nil {
		http.Error(w, "color not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		http.Error(w, "bambu token not configured", http.StatusBadRequest)
		return
	}

	adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
	filamentID := targetProduct.BambuPresetID
	if filamentID == "" {
		filamentID = getBambuFilamentID(targetProduct.Material)
	}

	for i := 0; i < req.Quantity; i++ {
		prefix := getInitial(targetProduct.Brand) + getInitial(targetColor.Name)
		shortCode, _ := s.st.NextShortCode(prefix)
		
		filamentName := fmt.Sprintf("%s %s %s", targetProduct.Brand, targetProduct.Material, targetColor.Name)
		if len(filamentName) > 40 {
			filamentName = filamentName[:40]
		}
		
		f := bambu.CloudFilament{
			FilamentID:   filamentID,
			FilamentName: filamentName,
			Color:        colorHexFromName(targetColor.Name) + "FF",
			NetWeight:    1000,
			Note:         fmt.Sprintf("%s (%s) - PandaSpool Sync", shortCode, targetColor.Name),
		}

		bambuCloudID, err := adapter.CreateFilament(f)
		if err != nil {
			if i > 0 {
				break // partial success, just return what we have
			}
			http.Error(w, fmt.Sprintf("failed to create cloud filament: %v", err), http.StatusInternalServerError)
			return
		}

		sp := store.Spool{
			ColorID:           req.ColorID,
			ShortCode:         shortCode,
			BambuCloudID:      bambuCloudID,
			BambuFilamentID:   filamentID,
			BambuFilamentName: filamentName,
			BambuRegion:       cfg.Bambu.Region,
			ColorHex:          colorHexFromName(targetColor.Name),
			NetWeightG:        1000,
			Status:            "unopened",
			SyncEnabled:       true,
		}

		_, err = s.st.SaveSpool(sp)
		if err != nil {
			if i > 0 {
				break
			}
			http.Error(w, fmt.Sprintf("failed to save local spool: %v", err), http.StatusInternalServerError)
			return
		}
	}

	s.spoolsList(w, r)
}

func (s *Server) spoolUpdateWeight(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		NetWeightG float64 `json:"net_weight_g"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
		adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
		err = adapter.UpdateWeight(spool.BambuCloudID, spool.BambuFilamentName, int(req.NetWeightG))
		if err != nil {
			// continue and save locally
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

	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	if req.Status == "depleted" {
		cfg := s.st.LoadSettings()
		if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
			adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
			adapter.DeleteFilaments([]int64{spool.BambuCloudID})
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
	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
		adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
		adapter.DeleteFilaments([]int64{spool.BambuCloudID})
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
