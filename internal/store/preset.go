package store

import (
	"archive/zip"
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"
)

type Preset struct {
	ID        string         `json:"id"`
	ProductID string         `json:"product_id"`
	ColorID   string         `json:"color_id,omitempty"`
	Name      string         `json:"name"`
	Authority string         `json:"authority"`
	SHA256    string         `json:"sha256"`
	MIME      string         `json:"mime"`
	Size      int64          `json:"size"`
	Note      string         `json:"note"`
	Fields    map[string]any `json:"fields"`
	CreatedAt string         `json:"created_at"`
}

func (s *Store) migratePresets() error {
	_, err := s.DB.Exec(`
CREATE TABLE IF NOT EXISTS presets (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL,
  color_id TEXT,
  name TEXT NOT NULL,
  authority TEXT NOT NULL DEFAULT 'manufacturer_profile',
  sha256 TEXT NOT NULL,
  mime TEXT NOT NULL DEFAULT '',
  size INTEGER NOT NULL DEFAULT 0,
  note TEXT NOT NULL DEFAULT '',
  fields TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL
);`)
	return err
}

func PresetDir(dataDir string) string {
	return filepath.Join(dataDir, "files", "presets")
}

var presetKeys = []string{
	"filament_vendor", "filament_type", "filament_id", "name",
	"filament_flow_ratio", "filament_max_volumetric_speed", "filament_density",
	"filament_diameter", "nozzle_temperature", "nozzle_temperature_range_low",
	"nozzle_temperature_range_high", "hot_plate_temp", "textured_plate_temp",
	"eng_plate_temp", "cool_plate_temp", "fan_min_speed", "fan_max_speed",
	"compatible_printers", "default_filament_colour",
}

func flattenScalar(v any) string {
	switch t := v.(type) {
	case nil:
		return ""
	case string:
		return strings.TrimSpace(t)
	case float64:
		if t == float64(int64(t)) {
			return fmt.Sprintf("%d", int64(t))
		}
		return strings.TrimRight(strings.TrimRight(fmt.Sprintf("%.4f", t), "0"), ".")
	case bool:
		if t {
			return "true"
		}
		return "false"
	case []any:
		if len(t) == 1 {
			return flattenScalar(t[0])
		}
		parts := make([]string, 0, len(t))
		for _, x := range t {
			if s := flattenScalar(x); s != "" {
				parts = append(parts, s)
			}
		}
		return strings.Join(parts, ", ")
	default:
		b, _ := json.Marshal(v)
		return string(b)
	}
}

func ExtractPresetFields(filename string, data []byte) (map[string]any, string, error) {
	entries, err := presetJSONEntries(filename, data)
	if err != nil {
		return nil, "", err
	}
	if len(entries) == 0 {
		return nil, "", fmt.Errorf("预设里没有 JSON")
	}
	payload := entries[0]
	out := map[string]any{}
	for _, k := range presetKeys {
		if v, ok := payload[k]; ok {
			s := flattenScalar(v)
			if s != "" {
				out[k] = s
			}
		}
	}
	name := flattenScalar(payload["name"])
	if name == "" {
		name = filename
	}
	return out, name, nil
}

func presetJSONEntries(filename string, data []byte) ([]map[string]any, error) {
	if zr, err := zip.NewReader(bytes.NewReader(data), int64(len(data))); err == nil {
		var out []map[string]any
		for _, f := range zr.File {
			low := strings.ToLower(f.Name)
			if !strings.HasSuffix(low, ".json") || strings.HasSuffix(low, "bundle_structure.json") {
				continue
			}
			rc, err := f.Open()
			if err != nil {
				continue
			}
			raw, _ := io.ReadAll(rc)
			rc.Close()
			var m map[string]any
			if json.Unmarshal(raw, &m) == nil {
				out = append(out, m)
			}
		}
		if len(out) == 0 {
			return nil, fmt.Errorf("%s 里没有耗材 JSON", filename)
		}
		return out, nil
	}
	var m map[string]any
	if err := json.Unmarshal(data, &m); err != nil {
		return nil, fmt.Errorf("不是 JSON 也不是 bbsflmt：%w", err)
	}
	return []map[string]any{m}, nil
}

func (s *Store) SavePreset(productID, colorID, origName, authority, note string, body []byte) (Preset, []Claim, error) {
	var empty Preset
	if productID == "" {
		return empty, nil, fmt.Errorf("未指定产品")
	}
	if len(body) == 0 || len(body) > MaxInboxBytes {
		return empty, nil, fmt.Errorf("预设空文件或超过 8MB")
	}
	fields, pname, err := ExtractPresetFields(origName, body)
	if err != nil {
		return empty, nil, err
	}
	sum := sha256.Sum256(body)
	sha := hex.EncodeToString(sum[:])
	if authority == "" {
		authority = "manufacturer_profile"
	}
	if err := os.MkdirAll(PresetDir(s.DataDir), 0o700); err != nil {
		return empty, nil, err
	}
	path := filepath.Join(PresetDir(s.DataDir), sha)
	if _, err := os.Stat(path); err != nil {
		if err := os.WriteFile(path, body, 0o600); err != nil {
			return empty, nil, err
		}
	}
	fb, _ := json.Marshal(fields)
	pr := Preset{
		ID: NewID(), ProductID: productID, ColorID: colorID, Name: pname,
		Authority: authority, SHA256: sha, Size: int64(len(body)),
		Note: note, Fields: fields, CreatedAt: time.Now().UTC().Format(time.RFC3339),
	}
	low := strings.ToLower(origName)
	switch {
	case strings.HasSuffix(low, ".bbsflmt"):
		pr.MIME = "application/zip"
	default:
		pr.MIME = "application/json"
	}
	var color any
	if colorID == "" {
		color = nil
	} else {
		color = colorID
	}
	_, err = s.DB.Exec(`INSERT INTO presets(id,product_id,color_id,name,authority,sha256,mime,size,note,fields,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)`,
		pr.ID, pr.ProductID, color, pr.Name, pr.Authority, pr.SHA256, pr.MIME, pr.Size, pr.Note, string(fb), pr.CreatedAt)
	if err != nil {
		return empty, nil, err
	}
	src := "资料"
	if authority == "bambu_system" {
		src = "Studio"
	} else if authority == "user_profile" {
		src = "实测"
	}
	var drafts []Claim
	for k, v := range fields {
		label := presetKeyLabel(k)
		c, err := s.SaveClaim(Claim{
			ProductID: productID, ColorID: colorID, Source: src,
			Key: label, Value: fmt.Sprint(v), Raw: "预设 " + pname + " / " + k,
			Status: ClaimDraft,
		})
		if err != nil {
			return pr, drafts, err
		}
		drafts = append(drafts, c)
	}
	return pr, drafts, nil
}

func presetKeyLabel(k string) string {
	m := map[string]string{
		"filament_flow_ratio":           "流量比例",
		"filament_max_volumetric_speed": "最大体积流量",
		"filament_density":              "密度",
		"filament_diameter":             "线径",
		"nozzle_temperature":            "喷嘴推荐温度",
		"nozzle_temperature_range_low":  "喷嘴温度下限",
		"nozzle_temperature_range_high": "喷嘴温度上限",
		"hot_plate_temp":                "热床推荐温度",
		"textured_plate_temp":           "纹理板温度",
		"eng_plate_temp":                "工程板温度",
		"cool_plate_temp":               "低温板温度",
		"fan_min_speed":                 "风扇最低",
		"fan_max_speed":                 "风扇最高",
		"compatible_printers":           "兼容机型",
		"filament_vendor":               "预设厂商",
		"filament_type":                 "预设材料类型",
		"name":                          "预设名称",
		"default_filament_colour":       "预设颜色",
	}
	if s, ok := m[k]; ok {
		return s
	}
	return k
}

func (s *Store) ListPresets(productID string) ([]Preset, error) {
	rows, err := s.DB.Query(`SELECT id,product_id,IFNULL(color_id,''),name,authority,sha256,mime,size,note,fields,created_at FROM presets WHERE product_id=? ORDER BY created_at DESC`, productID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Preset
	for rows.Next() {
		var p Preset
		var raw string
		if err := rows.Scan(&p.ID, &p.ProductID, &p.ColorID, &p.Name, &p.Authority, &p.SHA256, &p.MIME, &p.Size, &p.Note, &raw, &p.CreatedAt); err != nil {
			return nil, err
		}
		_ = json.Unmarshal([]byte(raw), &p.Fields)
		out = append(out, p)
	}
	if out == nil {
		out = []Preset{}
	}
	return out, rows.Err()
}

func (s *Store) DeletePreset(id string) error {
	_, err := s.DB.Exec(`DELETE FROM presets WHERE id=?`, id)
	return err
}

func (s *Store) EnsureColor(productID, name string) (Color, error) {
	name = strings.TrimSpace(name)
	if name == "" {
		return Color{}, fmt.Errorf("颜色名空")
	}
	var c Color
	err := s.DB.QueryRow(`SELECT id,product_id,name,color_family,unopened,opened,notes FROM colors WHERE product_id=? AND name=?`, productID, name).
		Scan(&c.ID, &c.ProductID, &c.Name, &c.ColorFamily, &c.Unopened, &c.Opened, &c.Notes)
	if err == nil {
		return c, nil
	}
	return s.SaveColor(Color{ProductID: productID, Name: name, ColorFamily: ClassifyColorFamily(name)})
}
