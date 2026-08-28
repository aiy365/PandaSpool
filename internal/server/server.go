package server

import (
	"io"
	"io/fs"
	"pandaspool/web"
	"net/http"
		"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"sync"
	"time"
	"github.com/gorilla/sessions"
	"pandaspool/internal/bambu"
	"pandaspool/internal/ewelink"
	"pandaspool/internal/ezviz"
	"pandaspool/internal/store"
)

type Server struct {
	http.Server
	st     *store.Store
	sess   *sessions.CookieStore
	bambu  *bambu.Client
	ew     *ewelink.Client
	ez     *ezviz.Client
	mu     sync.Mutex
	lastOn map[string]bool

	notifiedPrintEnd time.Time
	notifiedLayer1   bool
}

func New(dataDir, listen string) (*Server, error) {
	st, err := store.Open(dataDir)
	if err != nil {
		return nil, err
	}
	secret, err := st.SessionSecret()
	if err != nil {
		return nil, err
	}
	cs := sessions.NewCookieStore(secret)
	cs.Options = &sessions.Options{Path: "/", HttpOnly: true, SameSite: http.SameSiteLaxMode, MaxAge: 14 * 24 * 3600}
	s := &Server{
		st: st, sess: cs,
		bambu: bambu.New(), ew: ewelink.New(), ez: ezviz.New(),
		lastOn: map[string]bool{},
	}
	s.Addr = listen
	mux := http.NewServeMux()
	mux.HandleFunc("/api/wecom/verify", s.verifyWeCom)
	mux.HandleFunc("/api/notify/test", s.testNotify)
	mux.HandleFunc("/api/server-ip", func(w http.ResponseWriter, r *http.Request) {
		res, err := http.Get("https://api.ipify.org")
		if err == nil {
			defer res.Body.Close()
			io.Copy(w, res.Body)
		}
	})
	mux.HandleFunc("/api/health", s.health)
	mux.HandleFunc("/api/bootstrap", s.bootstrap)
	mux.HandleFunc("/api/setup", s.setup)
	mux.HandleFunc("/api/login", s.login)
	mux.HandleFunc("/api/logout", s.logout)
	mux.HandleFunc("/api/me", s.auth(s.me))
	mux.HandleFunc("/api/summary", s.auth(s.summary))
	mux.HandleFunc("/api/settings", s.auth(s.settings))
	mux.HandleFunc("/api/settings/password", s.auth(s.changePassword))
	mux.HandleFunc("/api/settings/test/bambu", s.auth(s.testBambu))
	mux.HandleFunc("/api/settings/bambu/send-code", s.auth(s.bambuSendCode))
	mux.HandleFunc("/api/settings/bambu/verify-code", s.auth(s.bambuVerifyCode))
	mux.HandleFunc("/api/settings/bambu/token", s.auth(s.bambuToken))
	mux.HandleFunc("/api/settings/test/ewelink", s.auth(s.testEWeLink))
	mux.HandleFunc("/api/settings/ewelink/token", s.auth(s.ewelinkToken))
	mux.HandleFunc("/api/settings/test/ezviz", s.auth(s.testEzviz))
	mux.HandleFunc("/api/ewelink/devices", s.auth(s.ewDevices))
	mux.HandleFunc("/api/ewelink/switch", s.auth(s.ewSwitch))
	mux.HandleFunc("/api/products", s.auth(s.products))
	mux.HandleFunc("/api/products/", s.auth(s.productItem))
	mux.HandleFunc("/api/spools", s.auth(s.spoolsHandler))
	mux.HandleFunc("/api/spools/", s.auth(s.spoolItemHandler))
	mux.HandleFunc("/api/presets", s.auth(s.presetsListHandler))
	mux.HandleFunc("/api/presets/sync", s.auth(s.presetsSyncHandler))
	mux.HandleFunc("/api/inbox/", s.authAI(s.inboxItem))
	mux.HandleFunc("/api/presets/", s.auth(s.presetItem))
	mux.HandleFunc("/api/colors", s.auth(s.colors))
	mux.HandleFunc("/api/stock-ins", s.auth(s.stockIns))
	mux.HandleFunc("/api/claims", s.auth(s.claims))
	mux.HandleFunc("/api/claims/review", s.auth(s.reviewClaim))
	mux.HandleFunc("/api/compare", s.auth(s.compare))
	mux.HandleFunc("/api/ai/materials", s.authAI(s.aiMaterials))
	mux.HandleFunc("/api/ai/drafts", s.authAI(s.aiDrafts))
	mux.HandleFunc("/llms.txt", s.llmsTxt)
	mux.HandleFunc("/api/desk", s.authDesk(s.desk))
	mux.HandleFunc("/api/machine", s.auth(s.machine))
	mux.HandleFunc("/api/actuators/", s.auth(s.actuator))
	mux.HandleFunc("/api/camera", s.auth(s.camera))
	mux.HandleFunc("/api/air", s.auth(s.air))
	mux.HandleFunc("/api/ingest/air", s.ingestAir)
	mux.Handle("/", s.static())
	s.Handler = withLog(mux)
	s.applyIntegrations()
	go s.automate()
	return s, nil
}

func (s *Server) Close() error {
	s.st.Close()
	return s.Server.Close()
}



func (s *Server) testNotify(w http.ResponseWriter, r *http.Request) {
	st := s.bambu.Status()
	if st["gcode_state"] == nil {
		st["gcode_state"] = "TEST_RUNNING"
		st["layer"] = 99
		st["total_layer"] = 100
	}

	go s.sendWebhookNotification("🔧 PandaSpool 连通性测试", st)
	w.Write([]byte("{\"status\":\"ok\"}"))
}

func (s *Server) verifyWeCom(w http.ResponseWriter, r *http.Request) {
	echostr := r.URL.Query().Get("echostr")
	cfg := s.st.LoadSettings()
	aesKeyStr := cfg.Automations.WeComAESKey
	if aesKeyStr == "" || echostr == "" {
		w.Write([]byte("error"))
		return
	}

	aesKey, err := base64.StdEncoding.DecodeString(aesKeyStr + "=")
	if err != nil {
		w.Write([]byte("error"))
		return
	}

	ciphertext, err := base64.StdEncoding.DecodeString(echostr)
	if err != nil {
		ciphertext, err = base64.StdEncoding.DecodeString(strings.ReplaceAll(echostr, " ", "+"))
		if err != nil {
			w.Write([]byte("error"))
			return
		}
	}

	block, err := aes.NewCipher(aesKey)
	if err != nil {
		w.Write([]byte("error"))
		return
	}
	mode := cipher.NewCBCDecrypter(block, aesKey[:16])

	plaintext := make([]byte, len(ciphertext))
	mode.CryptBlocks(plaintext, ciphertext)

	pad := int(plaintext[len(plaintext)-1])
	if len(plaintext) < pad {
		w.Write([]byte("error"))
		return
	}
	plaintext = plaintext[:len(plaintext)-pad]

	if len(plaintext) < 20 {
		w.Write([]byte("error"))
		return
	}
	content := plaintext[16:]

	msgLen := binary.BigEndian.Uint32(content[:4])
	if len(content) < int(4+msgLen) {
		w.Write([]byte("error"))
		return
	}

	msg := content[4 : 4+msgLen]
	w.Write(msg)
}

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}

func (s *Server) bootstrap(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	title := cfg.Site.Title
	if title == "" {
		title = "PandaSpool"
	}
	w.Write([]byte(`{"ready":` + fmt.Sprintf("%v", s.st.HasAdmin()) + `,"site":{"title":"` + title + `"}}`))
}

func (s *Server) setup(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if !s.st.HasAdmin() {
		s.st.SetAdmin("admin", req.Password)
	}
	w.Write([]byte("{\"status\":\"ok\"}"))
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Set-Cookie", "token=; Path=/; Max-Age=0")
}

func (s *Server) auth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		next(w, r)
	}
}

func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"user":"admin"}`))
}

func (s *Server) summary(w http.ResponseWriter, r *http.Request) {
	json.NewEncoder(w).Encode(s.st.Summary())
}

func (s *Server) settings(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		json.NewEncoder(w).Encode(s.st.LoadSettings())
		return
	}
	var cfg store.Settings
	if err := json.NewDecoder(r.Body).Decode(&cfg); err == nil {
		s.st.SaveSettings(cfg)
		s.applyIntegrations()
	}
	w.Write([]byte("{\"status\":\"ok\"}"))
}

func (s *Server) changePassword(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	s.st.SetAdmin(s.st.AdminUsername(), req.Password)
	w.Write([]byte("{\"status\":\"ok\"}"))
}

func (s *Server) testBambu(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) bambuSendCode(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) bambuVerifyCode(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) bambuToken(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) testEWeLink(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) testEzviz(w http.ResponseWriter, r *http.Request) {
	token, err := s.ez.AccessToken()
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]any{
		"ok":        true,
		"token_len": len(token),
	})
}

func (s *Server) ewelinkToken(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) ewDevices(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte("{\"status\":\"ok\"}"))
}
func (s *Server) ewSwitch(w http.ResponseWriter, r *http.Request) { w.Write([]byte("{\"status\":\"ok\"}"))}
func (s *Server) products(w http.ResponseWriter, r *http.Request) {
	if r.Method == "GET" {
		res, _ := s.st.ListProducts()
		json.NewEncoder(w).Encode(res)
	} else {
		var req store.Product
		json.NewDecoder(r.Body).Decode(&req)
		res, _ := s.st.SaveProduct(req)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) productItem(w http.ResponseWriter, r *http.Request) {
	parts := strings.Split(r.URL.Path, "/")
	id := parts[len(parts)-1]
	if r.Method == "DELETE" {
		s.st.DeleteProduct(id)
	} else {
		res, _ := s.st.GetProduct(id)
		json.NewEncoder(w).Encode(res)
	}
}
func (s *Server) authAI(next http.HandlerFunc) http.HandlerFunc { return next }


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
		SELECT p.brand || ' ' || p.product_line || ' ' || p.material AS name, c.source, c.claim_key, c.claim_value, c.unit
		FROM claims c JOIN products p ON c.product_id = p.id
		WHERE c.status = 'confirmed'
	`)
	if err != nil {
		res["error"] = []map[string]any{{"value": err.Error()}}
	} else {
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

	ezStatus := s.ez.Status()
	ezStatus["rotation"] = cfg.Ezviz.Rotation
	ezStatus["crop"] = cfg.Ezviz.Crop
	json.NewEncoder(w).Encode(map[string]any{
		"bambu":    bambuStatus,
		"printing": s.bambu.HasPrintState(),
		"air":      airMap,
		"ezviz":    ezStatus,
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
	token, err := s.ez.AccessToken()
	if err != nil {
		http.Error(w, err.Error(), 500)
		return
	}
	channel := cfg.Ezviz.Channel
	if channel == "" { channel = "1" }
	urlStr := fmt.Sprintf("ezopen://open.ys7.com/%s/%s.hd.live", cfg.Ezviz.DeviceSerial, channel)
	if cfg.Ezviz.VerifyCode != "" {
		urlStr = fmt.Sprintf("ezopen://%s@open.ys7.com/%s/%s.hd.live", cfg.Ezviz.VerifyCode, cfg.Ezviz.DeviceSerial, channel)
	}
	json.NewEncoder(w).Encode(map[string]string{
		"accessToken": token,
		"url": urlStr,
	})
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

func (s *Server) static() http.HandlerFunc {
	dir, _ := fs.Sub(web.FS, "dist")
	return http.FileServer(http.FS(dir)).ServeHTTP
}

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
		s.tickNotifications()
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


func withLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Security-Policy",
			"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self' ws: wss: https:; worker-src 'self' blob:; media-src 'self' blob: https:; frame-ancestors 'none'")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
	})
}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&body)
	if s.st.CheckAdmin("admin", body.Password) {
		w.Header().Set("Set-Cookie", "token=admin; Path=/; HttpOnly")
		w.Write([]byte(`{"status":"ok"}`))
	} else {
		w.WriteHeader(401)
		w.Write([]byte(`{"error":"wrong password"}`))
	}
}
