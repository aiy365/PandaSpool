package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"pandaspool/internal/bambu"
	"pandaspool/internal/store"
	"regexp"
	"sort"
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
	SpecCloudID int64  `json:"spec_cloud_id"`
	ColorName   string `json:"color_name"`
	ColorHex    string `json:"color_hex"`
	Quantity    int    `json:"quantity"`
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


func (s *Server) cloudAdapter() (*bambu.CloudAdapter, error) {
	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		return nil, fmt.Errorf("未配置拓竹云 token，请先到设置页登录拓竹")
	}
	return bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken), nil
}

// spoolNoteRe 从云端备注里提取 PandaSpool 短编号（如 pm001）。
var spoolNoteRe = regexp.MustCompile(`(?i)\b([a-z]{1,3}\d{3,4})\b`)

func SpoolCodeFromNote(note string) string {
	if m := spoolNoteRe.FindStringSubmatch(note); m != nil {
		return strings.ToLower(m[1])
	}
	return ""
}

// spoolCloudSync 拉取拓竹云端自定义耗材，返回可作"规格"的目录：
// 排除 PandaSpool 托管的卷（备注带短编号的），其余每条 = 一个规格标记物。
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
	type Spec struct {
		CloudID    int64  `json:"cloud_id"`
		FilamentID string `json:"filament_id"`
		Name       string `json:"name"`
		Vendor     string `json:"vendor"`
		Material   string `json:"material"`
		Color      string `json:"color"`
		NetWeight  int    `json:"net_weight"`
	}
	specs := make([]Spec, 0, len(filaments))
	for _, f := range filaments {
		if f.ID <= 0 || SpoolCodeFromNote(f.Note) != "" {
			continue
		}
		name := f.FilamentName
		if name == "" {
			name = f.FilamentID
		}
		specs = append(specs, Spec{
			CloudID:    f.ID,
			FilamentID: f.FilamentID,
			Name:       name,
			Vendor:     f.FilamentVendor,
			Material:   f.Category,
			Color:      f.Color,
			NetWeight:  f.NetWeight,
		})
	}
	sort.Slice(specs, func(i, j int) bool { return specs[i].Name < specs[j].Name })
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "specs": specs})
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

// spoolIntake 按云端规格 + 颜色 + 数量入库：每卷即时在拓竹云端建档
// （备注写短编号，回查精确匹配），本地生成料盘记录。
func (s *Server) spoolIntake(w http.ResponseWriter, r *http.Request) {
	var req intakeReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}
	req.ColorName = strings.TrimSpace(req.ColorName)
	if req.SpecCloudID <= 0 || req.ColorName == "" {
		jsonError(w, "要选规格并填颜色名", http.StatusBadRequest)
		return
	}
	if req.Quantity < 1 || req.Quantity > 100 {
		jsonError(w, "数量要在 1-100 之间", http.StatusBadRequest)
		return
	}
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
	var spec *bambu.CloudFilament
	for i := range filaments {
		f := filaments[i]
		if f.ID == req.SpecCloudID && SpoolCodeFromNote(f.Note) == "" {
			spec = &filaments[i]
			break
		}
	}
	if spec == nil {
		jsonError(w, "规格不存在或已变成托管卷，请重新点「同步对账」", http.StatusBadRequest)
		return
	}

	cfg := s.st.LoadSettings()
	colorHex := strings.TrimPrefix(strings.TrimSpace(req.ColorHex), "#")
	if len(colorHex) != 6 {
		colorHex = colorHexFromName(req.ColorName)
	}
	vendor := vendorOf(spec)
	prefix := strings.ToLower(getInitial(vendor) + getInitial(req.ColorName))
	baseName := strings.TrimSpace(spec.FilamentName)
	if baseName == "" {
		baseName = spec.FilamentID
	}
	netWeight := spec.NetWeight
	if netWeight <= 0 {
		netWeight = 1000
	}
	filamentID := spec.FilamentID
	if filamentID == "" {
		filamentID = getBambuFilamentID(spec.Category + " " + baseName)
	}

	created := make([]store.Spool, 0, req.Quantity)
	codes := make([]string, 0, req.Quantity)
	for i := 0; i < req.Quantity; i++ {
		code, err := s.st.NextShortCode(prefix)
		if err != nil {
			jsonError(w, err.Error(), http.StatusInternalServerError)
			return
		}
		name := bambu.TruncateRunes(strings.TrimSpace(baseName+" "+req.ColorName), 40)
		f := bambu.CloudFilament{
			FilamentID:   filamentID,
			FilamentName: name,
			Color:        colorHex + "FF",
			NetWeight:    netWeight,
			Note:         fmt.Sprintf("PandaSpool %s %s", code, req.ColorName),
		}
		cloudID, err := ad.CreateFilament(f)
		if err != nil {
			if i > 0 {
				break // 部分成功：返回已入库的部分
			}
			jsonError(w, fmt.Sprintf("云端建档失败：%v", err), http.StatusBadGateway)
			return
		}
		sp := store.Spool{
			ColorID:           "",
			ShortCode:         code,
			BambuCloudID:      cloudID,
			BambuVendor:       vendor,
			BambuFilamentName: name,
			BambuFilamentID:   filamentID,
			BambuRegion:       cfg.Bambu.Region,
			ColorHex:          colorHex,
			NetWeightG:        float64(netWeight),
			Status:            "unopened",
			SyncEnabled:       true,
		}
		saved, err := s.st.SaveSpool(sp)
		if err != nil {
			if i > 0 {
				break
			}
			jsonError(w, fmt.Sprintf("本地入库失败：%v", err), http.StatusInternalServerError)
			return
		}
		created = append(created, saved)
		codes = append(codes, code)
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "codes": codes, "spools": created})
}

// spoolCloudReconcile 云端对账：本地托管卷 vs 拓竹云端条目核对。
func (s *Server) spoolCloudReconcile(w http.ResponseWriter, r *http.Request) {
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
	spools, err := s.st.ListSpools()
	if err != nil {
		jsonError(w, err.Error(), http.StatusInternalServerError)
		return
	}
	cloudByID := map[int64]bambu.CloudFilament{}
	managed := []bambu.CloudFilament{}
	for _, f := range filaments {
		if f.ID <= 0 {
			continue
		}
		cloudByID[f.ID] = f
		if SpoolCodeFromNote(f.Note) != "" {
			managed = append(managed, f)
		}
	}
	type Matched struct {
		Spool     store.Spool `json:"spool"`
		CloudID   int64       `json:"cloud_id"`
		CloudNote string      `json:"cloud_note"`
	}
	matched := []Matched{}
	localOnly := []store.Spool{}
	depleted := 0
	inCloud := map[int64]bool{}
	for _, sp := range spools {
		if sp.Status == "depleted" {
			depleted++
			continue
		}
		if sp.BambuCloudID > 0 && cloudByID[sp.BambuCloudID].ID > 0 {
			inCloud[sp.BambuCloudID] = true
			matched = append(matched, Matched{Spool: sp, CloudID: sp.BambuCloudID, CloudNote: cloudByID[sp.BambuCloudID].Note})
		} else {
			localOnly = append(localOnly, sp)
		}
	}
	cloudOnly := []bambu.CloudFilament{}
	for _, f := range managed {
		if !inCloud[f.ID] {
			cloudOnly = append(cloudOnly, f)
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"ok": true, "matched": matched, "local_only": localOnly,
		"cloud_only": cloudOnly, "depleted": depleted,
	})
}

// spoolCloudRepair 给"本地有云端无"的盘补建云端条目并回绑 ID。
func (s *Server) spoolCloudRepair(w http.ResponseWriter, r *http.Request) {
	var req struct {
		SpoolID string `json:"spool_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil || req.SpoolID == "" {
		jsonError(w, "缺少 spool_id", http.StatusBadRequest)
		return
	}
	sp, err := s.st.GetSpool(req.SpoolID)
	if err != nil {
		jsonError(w, "料盘不存在", http.StatusNotFound)
		return
	}
	if sp.Status == "depleted" {
		jsonError(w, "已用完的盘不需要云端条目", http.StatusBadRequest)
		return
	}
	ad, err := s.cloudAdapter()
	if err != nil {
		jsonError(w, err.Error(), http.StatusBadRequest)
		return
	}
	if sp.BambuCloudID > 0 {
		filaments, err := ad.ListFilaments()
		if err == nil {
			for _, f := range filaments {
				if f.ID == sp.BambuCloudID {
					jsonOK(w)
					return
				}
			}
		}
	}
	colorHex := sp.ColorHex
	if len(colorHex) != 6 {
		colorHex = "a0a0a0"
	}
	cloudID, err := ad.CreateFilament(bambu.CloudFilament{
		FilamentID:   sp.BambuFilamentID,
		FilamentName: sp.BambuFilamentName,
		Color:        colorHex + "FF",
		NetWeight:    int(sp.NetWeightG),
		Note:         fmt.Sprintf("PandaSpool %s", sp.ShortCode),
	})
	if err != nil {
		jsonError(w, err.Error(), http.StatusBadGateway)
		return
	}
	sp.BambuCloudID = cloudID
	if _, err := s.st.SaveSpool(sp); err != nil {
		jsonError(w, err.Error(), http.StatusInternalServerError)
		return
	}
	jsonOK(w)
}

// spoolCloudDelete 清理"云端孤儿"：备注带 PandaSpool 编号但本地没有对应盘。
func (s *Server) spoolCloudDelete(w http.ResponseWriter, r *http.Request, idStr string) {
	var id int64
	if _, err := fmt.Sscanf(idStr, "%d", &id); err != nil || id <= 0 {
		jsonError(w, "无效的云端 ID", http.StatusBadRequest)
		return
	}
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
	for _, f := range filaments {
		if f.ID == id {
			if SpoolCodeFromNote(f.Note) == "" {
				jsonError(w, "这条不是 PandaSpool 托管的卷，不能在这里删", http.StatusBadRequest)
				return
			}
			if err := ad.DeleteFilaments([]int64{id}); err != nil {
				jsonError(w, err.Error(), http.StatusBadGateway)
				return
			}
			jsonOK(w)
			return
		}
	}
	jsonError(w, "云端没有这条了", http.StatusNotFound)
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

// spoolCloudHandler 路由：/api/spools/cloud/sync|reconcile|repair|{id}
func (s *Server) spoolCloudHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/spools/cloud/")
	switch {
	case r.Method == http.MethodPost && path == "sync":
		s.spoolCloudSync(w, r)
	case r.Method == http.MethodGet && path == "reconcile":
		s.spoolCloudReconcile(w, r)
	case r.Method == http.MethodPost && path == "repair":
		s.spoolCloudRepair(w, r)
	case r.Method == http.MethodDelete && path != "":
		s.spoolCloudDelete(w, r, path)
	default:
		http.Error(w, "not found", http.StatusNotFound)
	}
}
