import io

p = 'internal/server/spool_api.go'
src = io.open(p, encoding='utf-8').read()
start = src.index('func (s *Server) spoolIntake')
end = src.index('func (s *Server) spoolUpdateWeight')

NEW = r'''
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
		filamentID = getBambuFilamentID(spec.Material + " " + baseName)
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

'''

src = src[:start] + NEW + src[end:]

OLD_IMPORTS = '''import (
	"encoding/json"
	"fmt"
	"net/http"
	"pandaspool/internal/bambu"
	"pandaspool/internal/store"
	"strings"
	"github.com/mozillazg/go-pinyin"
)'''
NEW_IMPORTS = '''import (
	"encoding/json"
	"fmt"
	"net/http"
	"pandaspool/internal/bambu"
	"pandaspool/internal/store"
	"regexp"
	"sort"
	"strings"

	"github.com/mozillazg/go-pinyin"
)'''
assert OLD_IMPORTS in src, 'imports not found'
src = src.replace(OLD_IMPORTS, NEW_IMPORTS)

io.open(p, 'w', encoding='utf-8', newline='\n').write(src)
print('replaced OK')
