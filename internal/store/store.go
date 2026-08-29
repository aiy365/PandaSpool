package store

import (
	"crypto/rand"
	"database/sql"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"golang.org/x/crypto/bcrypt"
	_ "modernc.org/sqlite"
)

const productCols = `id,brand,product_line,material,bambu_preset_id,notes,created_at`

type Store struct {
	DB      *sql.DB
	DataDir string
}

func Open(dataDir string) (*Store, error) {
	if err := os.MkdirAll(dataDir, 0o700); err != nil {
		return nil, err
	}
	if err := os.MkdirAll(filepath.Join(dataDir, "files"), 0o700); err != nil {
		return nil, err
	}
	dsn := filepath.Join(dataDir, "app.sqlite3") + "?_pragma=busy_timeout(5000)&_pragma=foreign_keys(ON)&_pragma=journal_mode(WAL)"
	db, err := sql.Open("sqlite", dsn)
	if err != nil {
		return nil, err
	}
	s := &Store{DB: db, DataDir: dataDir}
	if err := s.migrate(); err != nil {
		return nil, err
	}
	if err := s.migrateClaimsGovernance(); err != nil {
		return nil, err
	}
	if err := s.migrateInbox(); err != nil {
		return nil, err
	}
	if err := s.migratePresets(); err != nil {
		return nil, err
	}
	if err := s.migrateStockIns(); err != nil {
		return nil, err
	}
	if err := s.reclassifyUnsetFamilies(); err != nil {
		return nil, err
	}
	if err := s.migrateSpools(); err != nil {
		return nil, err
	}
	_, _ = s.DB.Exec("ALTER TABLE products ADD COLUMN bambu_preset_id TEXT NOT NULL DEFAULT ''")

	cfg := s.LoadSettings()
	if cfg.AI.Token == "" {
		cfg.AI.Token = NewID()
		_ = s.SaveSettings(cfg)
	}
	return s, nil
}

func (s *Store) Close() error { return s.DB.Close() }

func (s *Store) migrate() error {
	_, err := s.DB.Exec(`
CREATE TABLE IF NOT EXISTS meta (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (
  k TEXT PRIMARY KEY,
  v TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS products (
  id TEXT PRIMARY KEY,
  brand TEXT NOT NULL DEFAULT '',
  product_line TEXT NOT NULL DEFAULT '',
  material TEXT NOT NULL DEFAULT '',
  notes TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS colors (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  color_family TEXT NOT NULL DEFAULT '',
  unopened INTEGER NOT NULL DEFAULT 0,
  opened INTEGER NOT NULL DEFAULT 0,
  notes TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS claims (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL,
  color_id TEXT,
  source TEXT NOT NULL,
  claim_key TEXT NOT NULL,
  claim_value TEXT NOT NULL,
  unit TEXT NOT NULL DEFAULT '',
  raw TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS air_samples (
  ts INTEGER NOT NULL,
  zone TEXT NOT NULL,
  payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS air_ts ON air_samples(ts);
CREATE TABLE IF NOT EXISTS machine_snapshots (
  ts INTEGER PRIMARY KEY,
  payload TEXT NOT NULL
);
`)
	return err
}

func NewID() string {
	var b [16]byte
	_, _ = rand.Read(b[:])
	return hex.EncodeToString(b[:])
}

func (s *Store) GetMeta(k string) (string, error) {
	var v string
	err := s.DB.QueryRow(`SELECT v FROM meta WHERE k=?`, k).Scan(&v)
	if err == sql.ErrNoRows {
		return "", nil
	}
	return v, err
}

func (s *Store) SetMeta(k, v string) error {
	_, err := s.DB.Exec(`INSERT INTO meta(k,v) VALUES(?,?) ON CONFLICT(k) DO UPDATE SET v=excluded.v`, k, v)
	return err
}

func (s *Store) HasAdmin() bool {
	v, _ := s.GetMeta("admin_username")
	return v != ""
}

func (s *Store) AdminUsername() string {
	v, _ := s.GetMeta("admin_username")
	return v
}

func (s *Store) SetAdmin(user, password string) error {
	hash, err := bcrypt.GenerateFromPassword([]byte(password), bcrypt.DefaultCost)
	if err != nil {
		return err
	}
	if err := s.SetMeta("admin_username", strings.TrimSpace(user)); err != nil {
		return err
	}
	return s.SetMeta("admin_password", string(hash))
}

func (s *Store) CheckAdmin(user, password string) bool {
	u, _ := s.GetMeta("admin_username")
	h, _ := s.GetMeta("admin_password")
	if u == "" || u != user {
		return false
	}
	return bcrypt.CompareHashAndPassword([]byte(h), []byte(password)) == nil
}

type Settings struct {
	Site struct {
		Title string `json:"title"`
	} `json:"site"`
	Bambu struct {
		Region      string `json:"region"`
		Account     string `json:"account"`
		Password    string `json:"password,omitempty"`
		PrinterSN   string `json:"printer_sn"`
		AccessToken string `json:"access_token,omitempty"`
	} `json:"bambu"`
	EWeLink struct {
		Region       string `json:"region"`
		Account      string `json:"account"`
		Password     string `json:"password,omitempty"`
		AppID        string `json:"app_id"`
		AppSecret    string `json:"app_secret"`
		AccessToken  string `json:"access_token,omitempty"`
		RefreshToken string `json:"refresh_token,omitempty"`
		Light        string `json:"light"`
		BoxAlways    string `json:"box_always"`
		BoxPrint     string `json:"box_print"`
		Room         string `json:"room"`
	} `json:"ewelink"`
	Ezviz struct {
		AppKey       string `json:"app_key"`
		AppSecret    string `json:"app_secret"`
		DeviceSerial string `json:"device_serial"`
		Channel      string `json:"channel"`
		VerifyCode   string `json:"verify_code"`
		Rotation     string `json:"rotation"`
		Crop         string `json:"crop"`
		AccessToken  string `json:"access_token,omitempty"`
		TokenExpireAt int64 `json:"token_expire_at,omitempty"`
	} `json:"ezviz"`
	Air struct {
		Token string `json:"token"`
	} `json:"air"`
	AI struct {
		Token string `json:"token"`
	} `json:"ai"`
	Automations struct {
		BoxAlwaysOn       bool   `json:"box_always_on"`
		PrintBoostMinutes int    `json:"print_boost_minutes"`
		RoomOnPresence    bool   `json:"room_on_presence"`
		LarkWebhook       string `json:"lark_webhook"`
		PushPlusToken     string `json:"pushplus_token"`
		WxPusherAppToken  string `json:"wxpusher_app_token"`
		WxPusherUID       string `json:"wxpusher_uid"`
		WeComCorpID       string `json:"wecom_corpid"`
		WeComSecret       string `json:"wecom_secret"`
		WeComAgentID      string `json:"wecom_agentid"`
		WeComAESKey       string `json:"wecom_aeskey"`
		WeComToUser       string `json:"wecom_touser"`
	} `json:"automations"`
}

func DefaultSettings() Settings {
	var s Settings
	s.Site.Title = "PandaSpool"
	s.Bambu.Region = "cn"
	s.EWeLink.Region = "cn"
	s.Ezviz.Channel = "1"
	s.Automations.BoxAlwaysOn = true
	s.Automations.PrintBoostMinutes = 30
	s.Automations.RoomOnPresence = true
	return s
}

func (s *Store) LoadSettings() Settings {
	out := DefaultSettings()
	var raw string
	err := s.DB.QueryRow(`SELECT v FROM settings WHERE k='app'`).Scan(&raw)
	if err != nil {
		return out
	}
	_ = json.Unmarshal([]byte(raw), &out)
	if out.Automations.PrintBoostMinutes <= 0 {
		out.Automations.PrintBoostMinutes = 30
	}
	if out.Site.Title == "" {
		out.Site.Title = "PandaSpool"
	}
	return out
}

func (s *Store) SaveSettings(in Settings) error {
	cur := s.LoadSettings()
	if in.Bambu.Password == "" {
		in.Bambu.Password = cur.Bambu.Password
	}
	if in.Bambu.AccessToken == "" {
		in.Bambu.AccessToken = cur.Bambu.AccessToken
	}
	newEWPass := in.EWeLink.Password != "" && in.EWeLink.Password != cur.EWeLink.Password
	ewAccountChanged := in.EWeLink.Account != "" && in.EWeLink.Account != cur.EWeLink.Account
	if in.EWeLink.Password == "" || in.EWeLink.Password == "********" {
		in.EWeLink.Password = cur.EWeLink.Password
	}
	if in.EWeLink.AppSecret == "" || in.EWeLink.AppSecret == "********" {
		in.EWeLink.AppSecret = cur.EWeLink.AppSecret
	}
	if (in.EWeLink.AccessToken == "" || in.EWeLink.AccessToken == "********") && !newEWPass && !ewAccountChanged {
		in.EWeLink.AccessToken = cur.EWeLink.AccessToken
	}
	if (in.EWeLink.RefreshToken == "" || in.EWeLink.RefreshToken == "********") && !newEWPass && !ewAccountChanged {
		in.EWeLink.RefreshToken = cur.EWeLink.RefreshToken
	}
	if in.Ezviz.AppSecret == "" || in.Ezviz.AppSecret == "********" {
		in.Ezviz.AppSecret = cur.Ezviz.AppSecret
	}
	if in.Ezviz.VerifyCode == "" || in.Ezviz.VerifyCode == "********" {
		in.Ezviz.VerifyCode = cur.Ezviz.VerifyCode
	}
	if in.Ezviz.AccessToken == "" || in.Ezviz.AccessToken == "********" {
		in.Ezviz.AccessToken = cur.Ezviz.AccessToken
	}
	if in.Ezviz.TokenExpireAt == 0 {
		in.Ezviz.TokenExpireAt = cur.Ezviz.TokenExpireAt
	}
	if in.Bambu.Password == "" || in.Bambu.Password == "********" {
		in.Bambu.Password = cur.Bambu.Password
	}
	if in.Bambu.AccessToken == "" || in.Bambu.AccessToken == "********" {
		in.Bambu.AccessToken = cur.Bambu.AccessToken
	}
	if in.Automations.WeComSecret == "" || in.Automations.WeComSecret == "********" {
		in.Automations.WeComSecret = cur.Automations.WeComSecret
	}
	if in.Automations.WeComAESKey == "" || in.Automations.WeComAESKey == "********" {
		in.Automations.WeComAESKey = cur.Automations.WeComAESKey
	}
	if in.Air.Token == "" {
		in.Air.Token = cur.Air.Token
	}
	if in.Air.Token == "" {
		in.Air.Token = NewID()
	}
	if in.AI.Token == "" {
		in.AI.Token = cur.AI.Token
	}
	if in.AI.Token == "" {
		in.AI.Token = NewID()
	}
	b, err := json.Marshal(in)
	if err != nil {
		return err
	}
	_, err = s.DB.Exec(`INSERT INTO settings(k,v) VALUES('app',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v`, string(b))
	return err
}

func Redact(in Settings) Settings {
	if in.Bambu.Password != "" {
		in.Bambu.Password = ""
	}
	if in.Bambu.AccessToken != "" {
		in.Bambu.AccessToken = "********"
	}
	if in.EWeLink.Password != "" {
		in.EWeLink.Password = ""
	}
	if in.EWeLink.AppSecret != "" {
		in.EWeLink.AppSecret = "********"
	}
	if in.EWeLink.AccessToken != "" {
		in.EWeLink.AccessToken = "********"
	}
	if in.EWeLink.RefreshToken != "" {
		in.EWeLink.RefreshToken = "********"
	}
	if in.Ezviz.AppSecret != "" {
		in.Ezviz.AppSecret = "********"
	}
	if in.Ezviz.VerifyCode != "" {
		in.Ezviz.VerifyCode = "********"
	}
	if in.Ezviz.AccessToken != "" {
		in.Ezviz.AccessToken = "********"
	}
	if in.Automations.WeComSecret != "" {
		in.Automations.WeComSecret = "********"
	}
	if in.Automations.WeComAESKey != "" {
		in.Automations.WeComAESKey = "********"
	}
	return in
}

type Product struct {
	ID          string            `json:"id"`
	Brand       string            `json:"brand"`
	ProductLine string            `json:"product_line"`
	Material    string            `json:"material"`
	BambuPresetID string            `json:"bambu_preset_id"`
	Notes       string            `json:"notes"`
	CreatedAt   string            `json:"created_at"`
	Colors      []Color           `json:"colors,omitempty"`
	Card        map[string]string `json:"card,omitempty"`
}

type Color struct {
	ID          string  `json:"id"`
	ProductID   string  `json:"product_id"`
	Name        string  `json:"name"`
	ColorFamily string  `json:"color_family"`
	Unopened    int     `json:"unopened"`
	Opened      int     `json:"opened"`
	Notes       string  `json:"notes"`
	AvgPrice    float64 `json:"avg_price"`
	BuyQty      float64 `json:"buy_qty"`
	BuyCost     float64 `json:"buy_cost,omitempty"`
}

type Claim struct {
	ID        string `json:"id"`
	ProductID string `json:"product_id"`
	ColorID   string `json:"color_id,omitempty"`
	Source    string `json:"source"`
	Key       string `json:"key"`
	Value     string `json:"value"`
	Unit      string `json:"unit"`
	Raw       string `json:"raw"`
	Status    string `json:"status"`
	CreatedAt string `json:"created_at,omitempty"`
}

const (
	ClaimDraft     = "draft"
	ClaimConfirmed = "confirmed"
	ClaimRejected  = "rejected"
)

func (s *Store) ListProducts() ([]Product, error) {
	rows, err := s.DB.Query(`SELECT ` + productCols + ` FROM products ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Product
	for rows.Next() {
		var p Product
		if err := rows.Scan(&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.BambuPresetID, &p.Notes, &p.CreatedAt); err != nil {
			return nil, err
		}
		cols, err := s.ListColors(p.ID)
		if err != nil {
			return nil, err
		}
		p.Colors = cols
		all, _ := s.ListClaims(p.ID)
		p.attachCard(all)
		out = append(out, p)
	}
	if out == nil {
		out = []Product{}
	}
	return out, rows.Err()
}

func (s *Store) GetProduct(id string) (Product, error) {
	var p Product
	err := s.DB.QueryRow(`SELECT `+productCols+` FROM products WHERE id=?`, id).
		Scan(&p.ID, &p.Brand, &p.ProductLine, &p.Material, &p.BambuPresetID, &p.Notes, &p.CreatedAt)
	if err != nil {
		return p, err
	}
	p.Colors, _ = s.ListColors(id)
	all, _ := s.ListClaims(id)
	p.attachCard(all)
	return p, nil
}

func (s *Store) SaveProduct(p Product) (Product, error) {
	if p.ID == "" {
		p.ID = NewID()
		p.CreatedAt = time.Now().UTC().Format(time.RFC3339)
		_, err := s.DB.Exec(`INSERT INTO products(`+productCols+`) VALUES(?,?,?,?,?,?,?)`,
			p.ID, p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.CreatedAt)
		return p, err
	}
	_, err := s.DB.Exec(`UPDATE products SET brand=?,product_line=?,material=?,bambu_preset_id=?,notes=? WHERE id=?`,
		p.Brand, p.ProductLine, p.Material, p.BambuPresetID, p.Notes, p.ID)
	return p, err
}

func (s *Store) DeleteProduct(id string) error {
	_, _ = s.DB.Exec(`DELETE FROM stock_ins WHERE color_id IN (SELECT id FROM colors WHERE product_id=?)`, id)
	_, _ = s.DB.Exec(`DELETE FROM colors WHERE product_id=?`, id)
	_, _ = s.DB.Exec(`DELETE FROM claims WHERE product_id=?`, id)
	_, _ = s.DB.Exec(`DELETE FROM inbox WHERE product_id=?`, id)
	_, _ = s.DB.Exec(`DELETE FROM presets WHERE product_id=?`, id)
	_, err := s.DB.Exec(`DELETE FROM products WHERE id=?`, id)
	return err
}

func (s *Store) ListColors(productID string) ([]Color, error) {
	rows, err := s.DB.Query(`SELECT id,product_id,name,color_family,unopened,opened,notes FROM colors WHERE product_id=?`, productID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Color
	for rows.Next() {
		var c Color
		if err := rows.Scan(&c.ID, &c.ProductID, &c.Name, &c.ColorFamily, &c.Unopened, &c.Opened, &c.Notes); err != nil {
			return nil, err
		}
		s.fillColorCost(&c)
		out = append(out, c)
	}
	if out == nil {
		out = []Color{}
	}
	return out, rows.Err()
}

func (s *Store) ListAllColors() ([]Color, error) {
	rows, err := s.DB.Query(`SELECT id,product_id,name,color_family,unopened,opened,notes FROM colors`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Color
	for rows.Next() {
		var c Color
		if err := rows.Scan(&c.ID, &c.ProductID, &c.Name, &c.ColorFamily, &c.Unopened, &c.Opened, &c.Notes); err != nil {
			return nil, err
		}
		s.fillColorCost(&c)
		out = append(out, c)
	}
	if out == nil {
		out = []Color{}
	}
	return out, rows.Err()
}

func (s *Store) SaveColor(c Color) (Color, error) {
	if c.Opened < 0 {
		c.Opened = 0
	}
	if c.Opened > 1 {
		c.Opened = 1
	}
	if c.Unopened < 0 {
		c.Unopened = 0
	}
	if strings.TrimSpace(c.ColorFamily) == "" {
		c.ColorFamily = ClassifyColorFamily(c.Name)
	}
	// Same merchant color name on one product is one row. Empty names stay distinct
	// catalog slots and are never merged.
	if c.ID == "" {
		if name := strings.TrimSpace(c.Name); name != "" && c.ProductID != "" {
			var existing string
			err := s.DB.QueryRow(`SELECT id FROM colors WHERE product_id=? AND name=?`, c.ProductID, name).Scan(&existing)
			if err == nil && existing != "" {
				c.ID = existing
			}
		}
	}
	if c.ID == "" {
		c.ID = NewID()
		_, err := s.DB.Exec(`INSERT INTO colors(id,product_id,name,color_family,unopened,opened,notes) VALUES(?,?,?,?,?,?,?)`,
			c.ID, c.ProductID, c.Name, c.ColorFamily, c.Unopened, c.Opened, c.Notes)
		return c, err
	}
	_, err := s.DB.Exec(`UPDATE colors SET name=?,color_family=?,unopened=?,opened=?,notes=? WHERE id=?`,
		c.Name, c.ColorFamily, c.Unopened, c.Opened, c.Notes, c.ID)
	return c, err
}

func (s *Store) DeleteColor(id string) error {
	_, _ = s.DB.Exec(`DELETE FROM stock_ins WHERE color_id=?`, id)
	_, err := s.DB.Exec(`DELETE FROM colors WHERE id=?`, id)
	return err
}

func (s *Store) ListClaims(productID string) ([]Claim, error) {
	return s.listClaims(`SELECT id,product_id,IFNULL(color_id,''),source,claim_key,claim_value,unit,raw,IFNULL(status,''),IFNULL(created_at,'') FROM claims WHERE product_id=?`, productID)
}

func (s *Store) ListClaimsByStatus(productID, status string) ([]Claim, error) {
	return s.listClaims(`SELECT id,product_id,IFNULL(color_id,''),source,claim_key,claim_value,unit,raw,IFNULL(status,''),IFNULL(created_at,'') FROM claims WHERE product_id=? AND status=?`, productID, status)
}

func (s *Store) listClaims(q string, args ...any) ([]Claim, error) {
	rows, err := s.DB.Query(q, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []Claim
	for rows.Next() {
		var c Claim
		if err := rows.Scan(&c.ID, &c.ProductID, &c.ColorID, &c.Source, &c.Key, &c.Value, &c.Unit, &c.Raw, &c.Status, &c.CreatedAt); err != nil {
			return nil, err
		}
		if c.Status == "" {
			c.Status = ClaimConfirmed
		}
		out = append(out, c)
	}
	if out == nil {
		out = []Claim{}
	}
	return out, rows.Err()
}

func (s *Store) SaveClaim(c Claim) (Claim, error) {
	c.Source = NormalizeSource(c.Source)
	c.Key = strings.TrimSpace(c.Key)
	c.Value = strings.TrimSpace(c.Value)
	c.Key = ClassifyTempKey(c.Key, c.Value, c.Source)
	c.Unit = strings.TrimSpace(c.Unit)
	if c.ProductID == "" || c.Key == "" {
		return c, fmt.Errorf("产品和字段不能空")
	}
	if c.ColorID != "" && !looksLikeID(c.ColorID) {
		col, err := s.EnsureColor(c.ProductID, c.ColorID)
		if err != nil {
			return c, err
		}
		c.ColorID = col.ID
	}
	if c.Status == "" {
		c.Status = ClaimConfirmed
	}
	if c.Status != ClaimDraft && c.Status != ClaimConfirmed && c.Status != ClaimRejected {
		return c, fmt.Errorf("未知状态")
	}
	// Same saying already on file: return it. Different saying is a new row.
	if c.ID == "" {
		var existing string
		err := s.DB.QueryRow(`SELECT id FROM claims WHERE product_id=? AND IFNULL(color_id,'')=? AND source=? AND claim_key=? AND claim_value=? AND unit=? AND status!=?`,
			c.ProductID, c.ColorID, c.Source, c.Key, c.Value, c.Unit, ClaimRejected).Scan(&existing)
		if err == nil && existing != "" {
			c.ID = existing
			_ = s.DB.QueryRow(`SELECT id,product_id,IFNULL(color_id,''),source,claim_key,claim_value,unit,raw,IFNULL(status,''),IFNULL(created_at,'') FROM claims WHERE id=?`, existing).
				Scan(&c.ID, &c.ProductID, &c.ColorID, &c.Source, &c.Key, &c.Value, &c.Unit, &c.Raw, &c.Status, &c.CreatedAt)
			return c, nil
		}
		c.ID = NewID()
		if c.CreatedAt == "" {
			c.CreatedAt = time.Now().UTC().Format(time.RFC3339)
		}
	}
	var color any
	if c.ColorID == "" {
		color = nil
	} else {
		color = c.ColorID
	}
	_, err := s.DB.Exec(`INSERT INTO claims(id,product_id,color_id,source,claim_key,claim_value,unit,raw,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)
		ON CONFLICT(id) DO UPDATE SET source=excluded.source,claim_key=excluded.claim_key,claim_value=excluded.claim_value,unit=excluded.unit,raw=excluded.raw,status=excluded.status`,
		c.ID, c.ProductID, color, c.Source, c.Key, c.Value, c.Unit, c.Raw, c.Status, c.CreatedAt)
	return c, err
}

func (s *Store) SetClaimStatus(id, status string) error {
	if status != ClaimDraft && status != ClaimConfirmed && status != ClaimRejected {
		return fmt.Errorf("未知状态")
	}
	res, err := s.DB.Exec(`UPDATE claims SET status=? WHERE id=?`, status, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return fmt.Errorf("找不到这条")
	}
	return nil
}

func (s *Store) ConfirmProductDrafts(productID string) (int, error) {
	if productID == "" {
		return 0, fmt.Errorf("产品不能空")
	}
	res, err := s.DB.Exec(`UPDATE claims SET status=? WHERE product_id=? AND status=?`, ClaimConfirmed, productID, ClaimDraft)
	if err != nil {
		return 0, err
	}
	n, _ := res.RowsAffected()
	return int(n), nil
}

func (s *Store) DeleteClaim(id string) error {
	_, err := s.DB.Exec(`DELETE FROM claims WHERE id=?`, id)
	return err
}

func (s *Store) InsertAir(ts int64, zone string, payload []byte) error {
	_, err := s.DB.Exec(`INSERT INTO air_samples(ts,zone,payload) VALUES(?,?,?)`, ts, zone, string(payload))
	return err
}

func (s *Store) RecentAir(limit int) ([]map[string]any, error) {
	if limit <= 0 {
		limit = 200
	}
	rows, err := s.DB.Query(`SELECT ts,zone,payload FROM air_samples ORDER BY ts DESC LIMIT ?`, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []map[string]any
	for rows.Next() {
		var ts int64
		var zone, payload string
		if err := rows.Scan(&ts, &zone, &payload); err != nil {
			return nil, err
		}
		var body any
		_ = json.Unmarshal([]byte(payload), &body)
		out = append(out, map[string]any{"ts": ts, "zone": zone, "data": body})
	}
	if out == nil {
		out = []map[string]any{}
	}
	return out, rows.Err()
}

func (s *Store) SaveSnapshot(payload []byte) error {
	_, err := s.DB.Exec(`INSERT INTO machine_snapshots(ts,payload) VALUES(?,?)
		ON CONFLICT(ts) DO UPDATE SET payload=excluded.payload`, time.Now().Unix(), string(payload))
	return err
}

func MustJSON(v any) string {
	b, err := json.Marshal(v)
	if err != nil {
		return "{}"
	}
	return string(b)
}

func (s *Store) SessionSecret() ([]byte, error) {
	v, err := s.GetMeta("session_secret")
	if err != nil {
		return nil, err
	}
	if v == "" {
		v = NewID() + NewID()
		if err := s.SetMeta("session_secret", v); err != nil {
			return nil, err
		}
	}
	return []byte(v), nil
}

func (s *Store) Summary() map[string]any {
	var products, colors, unopened, opened int
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM products`).Scan(&products)
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM colors`).Scan(&colors)
	_ = s.DB.QueryRow(`SELECT IFNULL(SUM(unopened),0), IFNULL(SUM(opened),0) FROM colors`).Scan(&unopened, &opened)
	return map[string]any{
		"products": products,
		"colors":   colors,
		"unopened": unopened,
		"opened":   opened,
		"spools":   unopened + opened,
	}
}

func looksLikeID(s string) bool {
	if len(s) < 16 {
		return false
	}
	for _, r := range s {
		if !((r >= '0' && r <= '9') || (r >= 'a' && r <= 'f') || (r >= 'A' && r <= 'F')) {
			return false
		}
	}
	return true
}

func Label(p Product) string {
	parts := []string{p.Brand, p.ProductLine, p.Material}
	var keep []string
	for _, x := range parts {
		if strings.TrimSpace(x) != "" {
			keep = append(keep, x)
		}
	}
	if len(keep) == 0 {
		return p.ID
	}
	return fmt.Sprintf("%s", strings.Join(keep, " / "))
}

func (s *Store) migrateSpools() error {
	_, err := s.DB.Exec(`CREATE TABLE IF NOT EXISTS spools (
		id TEXT PRIMARY KEY,
		color_id TEXT NOT NULL,
		bambu_cloud_id INTEGER NOT NULL,
		status TEXT NOT NULL DEFAULT 'opened',
		gross_weight_g REAL,
		empty_weight_g REAL,
		net_weight_g REAL NOT NULL,
		created_at TEXT NOT NULL
	)`)
	if err != nil {
		return err
	}

	columns := []string{
		"short_code TEXT",
		"bambu_vendor TEXT NOT NULL DEFAULT ''",
		"bambu_filament_name TEXT NOT NULL DEFAULT ''",
		"bambu_filament_id TEXT NOT NULL DEFAULT ''",
		"bambu_region TEXT NOT NULL DEFAULT 'cn'",
		"color_hex TEXT NOT NULL DEFAULT ''",
		"sync_enabled INTEGER NOT NULL DEFAULT 1",
		"last_synced_weight_g REAL",
		"last_synced_at TEXT",
	}

	for _, col := range columns {
		_, err := s.DB.Exec(fmt.Sprintf("ALTER TABLE spools ADD COLUMN %s", col))
		if err != nil && !strings.Contains(err.Error(), "duplicate column") {
			return err
		}
	}

	rows, err := s.DB.Query(`SELECT id FROM spools WHERE short_code IS NULL OR short_code = '' ORDER BY bambu_cloud_id ASC`)
	if err != nil {
		return err
	}
	defer rows.Close()

	var ids []string
	for rows.Next() {
		var id string
		if err := rows.Scan(&id); err != nil {
			return err
		}
		ids = append(ids, id)
	}
	rows.Close()

	if len(ids) == 0 {
		return nil
	}

	var maxCode sql.NullString
	err = s.DB.QueryRow(`SELECT short_code FROM spools WHERE short_code LIKE 'PP-%' ORDER BY CAST(SUBSTR(short_code, 4) AS INTEGER) DESC LIMIT 1`).Scan(&maxCode)
	if err != nil && err != sql.ErrNoRows {
		return err
	}

	var seq int
	if maxCode.Valid && maxCode.String != "" {
		_, _ = fmt.Sscanf(maxCode.String, "PP-%d", &seq)
	}

	for _, id := range ids {
		seq++
		code := fmt.Sprintf("PP-%03d", seq)
		_, err := s.DB.Exec(`UPDATE spools SET short_code = ? WHERE id = ?`, code, id)
		if err != nil {
			return err
		}
	}

	_, _ = s.DB.Exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_spools_short_code ON spools(short_code) WHERE short_code IS NOT NULL AND short_code != ''")

	return nil
}
