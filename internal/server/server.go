package server

import (
	"crypto/aes"
	"crypto/cipher"
	"encoding/base64"
	"encoding/binary"
	"encoding/json"
	"fmt"
	"io"
	"io/fs"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/sessions"
	"pandaspool/internal/bambu"
	"pandaspool/internal/ewelink"
	"pandaspool/internal/ezviz"
	"pandaspool/internal/store"
	"pandaspool/web"
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
	// eWeLink 客户端在 401/406 后会自动重登，新 token 通过回调落库，重启不丢。
	s.ew.OnTokenRefresh(func(at, rt string) {
		cfg := s.st.LoadSettings()
		cfg.EWeLink.AccessToken = at
		cfg.EWeLink.RefreshToken = rt
		_ = s.st.SaveSettings(cfg)
	})
	s.Addr = listen
	mux := http.NewServeMux()
	mux.HandleFunc("/api/wecom/verify", s.verifyWeCom)
	mux.HandleFunc("/api/notify/test", s.auth(s.testNotify))
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
	mux.HandleFunc("/api/presets/", s.auth(s.presetItem))
	mux.HandleFunc("/api/inbox/", s.authAny(s.inboxItem))
	mux.HandleFunc("/api/colors", s.auth(s.colors))
	mux.HandleFunc("/api/stock-ins", s.auth(s.stockIns))
	mux.HandleFunc("/api/claims", s.auth(s.claims))
	mux.HandleFunc("/api/claims/review", s.auth(s.reviewClaim))
	mux.HandleFunc("/api/compare", s.auth(s.compare))
	mux.HandleFunc("/api/ai/materials", s.authAI(s.aiMaterials))
	mux.HandleFunc("/api/ai/drafts", s.authAI(s.aiDrafts))
	mux.HandleFunc("/llms.txt", s.authAI(s.llmsTxt))
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

// ---- 鉴权 ----
// 页面用户走 cookie 会话；ESP32 空气探头走空气令牌；AI/桌面端走 AI 令牌。

const sessionName = "pp"

func (s *Server) sessionUser(r *http.Request) string {
	sess, err := s.sess.Get(r, sessionName)
	if err != nil {
		return ""
	}
	u, _ := sess.Values["user"].(string)
	return u
}

func (s *Server) auth(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if s.sessionUser(r) == "" {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"error":"未登录"}`))
			return
		}
		next(w, r)
	}
}

func bearerToken(r *http.Request) string {
	return strings.TrimSpace(strings.TrimPrefix(r.Header.Get("Authorization"), "Bearer "))
}

// authAny：会话或 AI 令牌任一通过。收集箱图片在浏览器 <img> 里用会话，
// AI 打包结果里的图片 URL 用令牌。
func (s *Server) authAny(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if s.sessionUser(r) != "" || s.aiTokenOK(r) {
			next(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte(`{"error":"未登录"}`))
	}
}

func (s *Server) aiTokenOK(r *http.Request) bool {
	cfg := s.st.LoadSettings()
	tok := bearerToken(r)
	return cfg.AI.Token != "" && tok == cfg.AI.Token
}

func (s *Server) authAI(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if !s.aiTokenOK(r) {
			w.Header().Set("Content-Type", "application/json")
			w.WriteHeader(http.StatusUnauthorized)
			w.Write([]byte(`{"error":"AI 令牌无效"}`))
			return
		}
		next(w, r)
	}
}

func (s *Server) authDesk(next http.HandlerFunc) http.HandlerFunc { return s.authAI(next) }

// ---- 基础 ----

func (s *Server) health(w http.ResponseWriter, r *http.Request) {
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) bootstrap(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	title := cfg.Site.Title
	if title == "" {
		title = "PandaSpool"
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"ready":` + fmt.Sprintf("%v", s.st.HasAdmin()) + `,"needs_setup":` + fmt.Sprintf("%v", !s.st.HasAdmin()) + `,"site":{"title":"` + title + `"}}`))
}

func (s *Server) setup(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Title    string `json:"title"`
		Username string `json:"username"`
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if s.st.HasAdmin() {
		w.Write([]byte(`{"status":"ok"}`))
		return
	}
	if len(req.Password) < 6 {
		http.Error(w, "密码至少 6 位", http.StatusBadRequest)
		return
	}
	user := strings.TrimSpace(req.Username)
	if user == "" {
		user = "admin"
	}
	if err := s.st.SetAdmin(user, req.Password); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if title := strings.TrimSpace(req.Title); title != "" {
		cfg := s.st.LoadSettings()
		cfg.Site.Title = title
		_ = s.st.SaveSettings(cfg)
	}
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) login(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	json.NewDecoder(r.Body).Decode(&body)
	user := strings.TrimSpace(body.Username)
	if user == "" {
		user = s.st.AdminUsername()
	}
	if !s.st.CheckAdmin(user, body.Password) {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte(`{"error":"用户名或密码不对"}`))
		return
	}
	sess, _ := s.sess.Get(r, sessionName)
	sess.Values["user"] = user
	if err := sess.Save(r, w); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) logout(w http.ResponseWriter, r *http.Request) {
	sess, _ := s.sess.Get(r, sessionName)
	sess.Options.MaxAge = -1
	_ = sess.Save(r, w)
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) me(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"user":     s.sessionUser(r),
		"username": s.sessionUser(r),
		"title":    cfg.Site.Title,
	})
}

// ---- 总览 ----

func (s *Server) summary(w http.ResponseWriter, r *http.Request) {
	out := s.st.Summary()
	st := s.bambu.Status()
	gcode, _ := st["gcode_state"].(string)
	stage, _ := st["stage"].(string)
	out["machine"] = st
	out["printing"] = bambu.PrintingFromState(gcode, stage)
	// RecentAir 返回的 data 是已解析的 JSON 体，不是 payload 字符串。
	if recent, err := s.st.RecentAir(1); err == nil && len(recent) > 0 {
		air := map[string]any{}
		if data, ok := recent[0]["data"].(map[string]any); ok {
			for k, v := range data {
				air[k] = v
			}
		}
		air["ts"] = recent[0]["ts"]
		out["air"] = air
	} else {
		out["air"] = map[string]any{}
	}
	drafts, _ := s.st.GovernanceCounts()
	out["drafts"] = drafts
	out["inbox"] = s.st.InboxPendingCount("")
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(out)
}

// ---- 设置 ----

func (s *Server) settings(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method == http.MethodGet {
		json.NewEncoder(w).Encode(store.Redact(s.st.LoadSettings()))
		return
	}
	var cfg store.Settings
	if err := json.NewDecoder(r.Body).Decode(&cfg); err == nil {
		if err := s.st.SaveSettings(cfg); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		s.applyIntegrations()
	}
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) changePassword(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Username    string `json:"username"`
		OldPassword string `json:"old_password"`
		NewPassword string `json:"new_password"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	current := s.st.AdminUsername()
	if !s.st.CheckAdmin(current, req.OldPassword) {
		http.Error(w, "原密码不对", http.StatusUnauthorized)
		return
	}
	if len(req.NewPassword) < 6 {
		http.Error(w, "新密码至少 6 位", http.StatusBadRequest)
		return
	}
	user := strings.TrimSpace(req.Username)
	if user == "" {
		user = current
	}
	if err := s.st.SetAdmin(user, req.NewPassword); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Write([]byte(`{"status":"ok"}`))
}

// ---- 拓竹 ----

func (s *Server) testBambu(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.bambu.Status())
}

func (s *Server) bambuSendCode(w http.ResponseWriter, r *http.Request) {
	if err := s.bambu.SendCode(); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "hint": "验证码已发送，去手机/邮箱查收后填入"})
}

func (s *Server) bambuVerifyCode(w http.ResponseWriter, r *http.Request) {
	var req struct {
		Code string `json:"code"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if err := s.bambu.LoginWithCode(req.Code); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	s.persistBambuToken()
	json.NewEncoder(w).Encode(s.bambu.Status())
}

func (s *Server) bambuToken(w http.ResponseWriter, r *http.Request) {
	var req struct {
		AccessToken string `json:"access_token"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if err := s.bambu.ApplyToken(req.AccessToken); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	s.persistBambuToken()
	json.NewEncoder(w).Encode(s.bambu.Status())
}

func (s *Server) persistBambuToken() {
	tok := s.bambu.Token()
	if tok == "" {
		return
	}
	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == tok {
		return
	}
	cfg.Bambu.AccessToken = tok
	_ = s.st.SaveSettings(cfg)
}

// ---- 易微联 ----

func (s *Server) testEWeLink(w http.ResponseWriter, r *http.Request) {
	if err := s.ew.Login(); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	devs, err := s.ew.Devices()
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	s.persistEWeLinkTokens()
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "devices": devs})
}

func (s *Server) ewelinkToken(w http.ResponseWriter, r *http.Request) {
	var req struct {
		AccessToken string `json:"access_token"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if err := s.ew.ApplyToken(req.AccessToken); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	devs, err := s.ew.Devices()
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	s.persistEWeLinkTokens()
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "devices": devs})
}

func (s *Server) persistEWeLinkTokens() {
	at, rt := s.ew.Tokens()
	if at == "" {
		return
	}
	cfg := s.st.LoadSettings()
	if cfg.EWeLink.AccessToken == at && cfg.EWeLink.RefreshToken == rt {
		return
	}
	cfg.EWeLink.AccessToken = at
	cfg.EWeLink.RefreshToken = rt
	_ = s.st.SaveSettings(cfg)
}

func (s *Server) ewDevices(w http.ResponseWriter, r *http.Request) {
	devs, err := s.ew.Devices()
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "devices": devs})
}

func (s *Server) ewSwitch(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID string `json:"id"`
		On bool   `json:"on"`
	}
	json.NewDecoder(r.Body).Decode(&req)
	if err := s.ew.Switch(req.ID, req.On); err != nil {
		json.NewEncoder(w).Encode(map[string]any{"error": err.Error()})
		return
	}
	json.NewEncoder(w).Encode(map[string]any{"ok": true})
}

// ---- 萤石 ----

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

// ---- 产品 / 颜色 ----

func (s *Server) products(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if r.Method == "GET" {
		res, err := s.st.ListProducts()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(res)
		return
	}
	var req store.Product
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	res, err := s.st.SaveProduct(req)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	json.NewEncoder(w).Encode(res)
}

func (s *Server) productItem(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/products/")
	parts := strings.Split(path, "/")
	id := parts[0]
	w.Header().Set("Content-Type", "application/json")

	// /api/products/{id}/inbox —— 收集箱批量上传
	if len(parts) == 2 && parts[1] == "inbox" {
		if r.Method == http.MethodPost {
			s.inboxUpload(w, r, id)
			return
		}
		if r.Method == http.MethodGet {
			items, err := s.st.ListInbox(id)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			out := make([]map[string]any, 0, len(items))
			for _, it := range items {
				out = append(out, store.InboxPublic(it))
			}
			json.NewEncoder(w).Encode(out)
			return
		}
	}

	// /api/products/{id}/presets —— 预设上传
	if len(parts) == 2 && parts[1] == "presets" {
		if r.Method == http.MethodPost {
			s.presetUpload(w, r, id)
			return
		}
		if r.Method == http.MethodGet {
			list, err := s.st.ListPresets(id)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			json.NewEncoder(w).Encode(list)
			return
		}
	}

	if r.Method == http.MethodDelete {
		if err := s.st.DeleteProduct(id); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
		return
	}
	p, err := s.st.GetProduct(id)
	if err != nil {
		http.Error(w, "产品不存在", http.StatusNotFound)
		return
	}
	// 前端产品页直接在这个对象上取扩展字段。
	raw, _ := json.Marshal(p)
	var out map[string]any
	_ = json.Unmarshal(raw, &out)
	if conflicts, err := s.st.ProductConflicts(id); err == nil {
		out["conflicts"] = conflicts
	}
	out["stock_ins"], _ = s.st.ListStockInsByProduct(id)
	items, _ := s.st.ListInbox(id)
	inbox := make([]map[string]any, 0, len(items))
	for _, it := range items {
		inbox = append(inbox, store.InboxPublic(it))
	}
	out["inbox"] = inbox
	out["presets"], _ = s.st.ListPresets(id)
	json.NewEncoder(w).Encode(out)
}

// ---- 颜色 ----

func (s *Server) colors(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		q := r.URL.Query().Get("product_id")
		var res []store.Color
		var err error
		if q == "" {
			res, err = s.st.ListAllColors()
		} else {
			res, err = s.st.ListColors(q)
		}
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(res)
	case http.MethodDelete:
		id := r.URL.Query().Get("id")
		if id == "" {
			http.Error(w, "缺少 id", http.StatusBadRequest)
			return
		}
		if err := s.st.DeleteColor(id); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
	default:
		var req store.Color
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		res, err := s.st.SaveColor(req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(res)
	}
}

// ---- 参数（claims） ----

func (s *Server) claims(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		q := r.URL.Query().Get("product_id")
		res, err := s.st.ListClaims(q)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(res)
	case http.MethodDelete:
		id := r.URL.Query().Get("id")
		if id == "" {
			http.Error(w, "缺少 id", http.StatusBadRequest)
			return
		}
		if err := s.st.DeleteClaim(id); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
	default:
		var req store.Claim
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		res, err := s.st.SaveClaim(req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		json.NewEncoder(w).Encode(res)
	}
}

func (s *Server) reviewClaim(w http.ResponseWriter, r *http.Request) {
	var req struct {
		ID        string `json:"id"`
		ProductID string `json:"product_id"`
		Status    string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	if req.ProductID != "" {
		n, err := s.st.ConfirmProductDrafts(req.ProductID)
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(map[string]any{"ok": true, "updated": n})
		return
	}
	if req.ID == "" {
		http.Error(w, "缺少 id 或 product_id", http.StatusBadRequest)
		return
	}
	if err := s.st.SetClaimStatus(req.ID, req.Status); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	w.Write([]byte(`{"status":"ok"}`))
}

// ---- 入库记账 ----

func (s *Server) stockIns(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	switch r.Method {
	case http.MethodGet:
		if pid := r.URL.Query().Get("product_id"); pid != "" {
			res, err := s.st.ListStockInsByProduct(pid)
			if err != nil {
				http.Error(w, err.Error(), http.StatusInternalServerError)
				return
			}
			json.NewEncoder(w).Encode(res)
			return
		}
		res, err := s.st.ListStockIns(r.URL.Query().Get("color_id"))
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		json.NewEncoder(w).Encode(res)
	default:
		var req store.StockIn
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		res, err := s.st.SaveStockIn(req)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		json.NewEncoder(w).Encode(res)
	}
}

// ---- 收集箱 ----

func (s *Server) inboxUpload(w http.ResponseWriter, r *http.Request, productID string) {
	if err := r.ParseMultipartForm(store.MaxInboxBytes); err != nil {
		http.Error(w, "图片太大或格式不对", http.StatusBadRequest)
		return
	}
	colorID := r.FormValue("color_id")
	files := r.MultipartForm.File["files"]
	if len(files) == 0 {
		http.Error(w, "没有收到图片", http.StatusBadRequest)
		return
	}
	if len(files) > store.MaxInboxBatch {
		http.Error(w, fmt.Sprintf("一次最多 %d 张", store.MaxInboxBatch), http.StatusBadRequest)
		return
	}
	var saved []map[string]any
	for _, fh := range files {
		f, err := fh.Open()
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		body, err := io.ReadAll(f)
		f.Close()
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		it, err := s.st.SaveInboxFile(productID, colorID, fh.Filename, body)
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		saved = append(saved, store.InboxPublic(it))
	}
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "items": saved, "hint": fmt.Sprintf("已收 %d 张", len(saved))})
}

func (s *Server) inboxItem(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/inbox/")
	parts := strings.Split(path, "/")
	id := parts[0]
	w.Header().Set("Content-Type", "application/json")

	// /api/inbox/{id}/file —— 图片本体
	if len(parts) == 2 && parts[1] == "file" && r.Method == http.MethodGet {
		it, err := s.st.GetInbox(id)
		if err != nil {
			http.Error(w, "图片不存在", http.StatusNotFound)
			return
		}
		body, err := os.ReadFile(store.InboxPath(s.st.DataDir, it.SHA256))
		if err != nil {
			http.Error(w, "文件缺失", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", it.MIME)
		w.Header().Set("Cache-Control", "private, max-age=86400")
		w.Write(body)
		return
	}

	switch r.Method {
	case http.MethodDelete:
		if err := s.st.DeleteInbox(id); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
	case http.MethodPost:
		// /api/inbox/{id}/processed —— 标记处理完
		var status string
		if len(parts) == 2 && parts[1] == "processed" {
			status = store.InboxProcessed
		} else {
			var req struct {
				Status string `json:"status"`
			}
			json.NewDecoder(r.Body).Decode(&req)
			status = req.Status
		}
		if err := s.st.SetInboxStatus(id, status); err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
	default:
		it, err := s.st.GetInbox(id)
		if err != nil {
			http.Error(w, "图片不存在", http.StatusNotFound)
			return
		}
		json.NewEncoder(w).Encode(store.InboxPublic(it))
	}
}

// ---- 预设 ----

func (s *Server) presetUpload(w http.ResponseWriter, r *http.Request, productID string) {
	if err := r.ParseMultipartForm(store.MaxInboxBytes); err != nil {
		http.Error(w, "文件太大", http.StatusBadRequest)
		return
	}
	file, header, err := r.FormFile("file")
	if err != nil {
		http.Error(w, "没有收到文件", http.StatusBadRequest)
		return
	}
	defer file.Close()
	body, err := io.ReadAll(file)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	pr, drafts, err := s.st.SavePreset(productID, r.FormValue("color_id"), header.Filename, r.FormValue("authority"), r.FormValue("note"), body)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	json.NewEncoder(w).Encode(map[string]any{
		"ok":   true,
		"item": pr,
		"hint": fmt.Sprintf("已抽出 %d 条草稿，去「待确认草稿」里核对", len(drafts)),
	})
}

func (s *Server) presetItem(w http.ResponseWriter, r *http.Request) {
	id := strings.TrimPrefix(r.URL.Path, "/api/presets/")
	w.Header().Set("Content-Type", "application/json")
	if r.Method == http.MethodDelete {
		if err := s.st.DeletePreset(id); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		w.Write([]byte(`{"status":"ok"}`))
		return
	}
	w.Write([]byte(`{"status":"ok"}`))
}

// ---- 横评 / AI ----

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
				"source":  source,
				"value":   value,
				"unit":    unit,
			})
		}
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(res)
}

func (s *Server) aiMaterials(w http.ResponseWriter, r *http.Request) {
	pack, err := s.st.AIPack()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(pack)
}

func (s *Server) aiDrafts(w http.ResponseWriter, r *http.Request) {
	var body json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	var list []store.Claim
	// 支持直接传数组，或 {"drafts": [...]} / {"product_id":..., "drafts":[...]}
	var arr []store.Claim
	if json.Unmarshal(body, &arr) == nil && arr != nil {
		list = arr
	} else {
		var wrap struct {
			Drafts []store.Claim `json:"drafts"`
		}
		if json.Unmarshal(body, &wrap) != nil || wrap.Drafts == nil {
			http.Error(w, "需要 drafts 数组", http.StatusBadRequest)
			return
		}
		list = wrap.Drafts
	}
	saved, err := s.st.SaveDrafts(list)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "saved": saved})
}

func (s *Server) llmsTxt(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.Write([]byte(`PandaSpool 材料档案 API（AI 只读 + 起草）

鉴权: Authorization: Bearer <AI 令牌>（设置页可查）

GET  /api/ai/materials   全部产品、颜色、库存、已确认参数、草稿、冲突、收集箱
POST /api/ai/drafts      提交草稿，body 为 claims 数组或 {"drafts":[...]}
                         字段: product_id, color_id(可选), source(资料/Studio/实测),
                               key, value, unit, raw
规则: 系统记住所有说法；人确认后才算数；冲突并存不覆盖；AI 只起草稿。
`))
}

// ---- 机台 / 执行器 / 摄像头 / 空气 ----

func (s *Server) desk(w http.ResponseWriter, r *http.Request) { s.machine(w, r) }

func (s *Server) machine(w http.ResponseWriter, r *http.Request) {
	bambuStatus := s.bambu.Status()
	cfg := s.st.LoadSettings()

	airMap := map[string]any{}
	if recent, err := s.st.RecentAir(1); err == nil && len(recent) > 0 {
		if data, ok := recent[0]["data"].(map[string]any); ok {
			for k, v := range data {
				airMap[k] = v
			}
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
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{
		"bambu":    bambuStatus,
		"printing": s.bambu.HasPrintState(),
		"air":      airMap,
		"ezviz":    ezStatus,
	})
}

func (s *Server) actuator(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	id := strings.TrimPrefix(r.URL.Path, "/api/actuators/")
	var body struct {
		On bool `json:"on"`
	}
	json.NewDecoder(r.Body).Decode(&body)

	cfg := s.st.LoadSettings()
	var ref string
	switch id {
	case "light":
		ref = cfg.EWeLink.Light
	case "box_always":
		ref = cfg.EWeLink.BoxAlways
	case "box_print", "exhaust":
		ref = cfg.EWeLink.BoxPrint
	case "room":
		ref = cfg.EWeLink.Room
	}

	if ref == "" {
		http.Error(w, "这一路还没绑定设备", http.StatusBadRequest)
		return
	}
	if err := s.ew.Switch(ref, body.On); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	s.mu.Lock()
	s.lastOn[ref] = body.On
	s.mu.Unlock()
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
	if channel == "" {
		channel = "1"
	}
	urlStr := fmt.Sprintf("ezopen://open.ys7.com/%s/%s.hd.live", cfg.Ezviz.DeviceSerial, channel)
	if cfg.Ezviz.VerifyCode != "" {
		urlStr = fmt.Sprintf("ezopen://%s@open.ys7.com/%s/%s.hd.live", cfg.Ezviz.VerifyCode, cfg.Ezviz.DeviceSerial, channel)
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"accessToken": token,
		"url":         urlStr,
	})
}

func (s *Server) air(w http.ResponseWriter, r *http.Request) {
	recent, err := s.st.RecentAir(50)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(recent)
}

func (s *Server) ingestAir(w http.ResponseWriter, r *http.Request) {
	cfg := s.st.LoadSettings()
	tok := bearerToken(r)
	if cfg.Air.Token == "" || tok != cfg.Air.Token {
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusUnauthorized)
		w.Write([]byte(`{"error":"空气令牌无效"}`))
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var payload map[string]any
	if err := json.NewDecoder(r.Body).Decode(&payload); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	ts := time.Now().Unix()
	if v, ok := payload["ts"].(float64); ok && v > 0 {
		if v > 1e12 {
			v /= 1000
		}
		ts = int64(v)
	}
	zone, _ := payload["zone"].(string)
	if zone == "" {
		zone = "room"
	}
	raw, _ := json.Marshal(payload)
	if err := s.st.InsertAir(ts, zone, raw); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Write([]byte(`{"status":"ok"}`))
}

// ---- 通知 ----

func (s *Server) testNotify(w http.ResponseWriter, r *http.Request) {
	st := s.bambu.Status()
	if st["gcode_state"] == nil {
		st["gcode_state"] = "TEST_RUNNING"
		st["layer"] = 99
		st["total_layer"] = 100
	}

	go s.sendWebhookNotification("🔧 PandaSpool 连通性测试", st)
	w.Write([]byte(`{"status":"ok"}`))
}

// ---- 其它 ----

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

// automate 每 10 秒巡检一次。开关命令只在目标状态和上次下发不一致时才发，
// 避免每 10 秒对同一个插座重复下发。
func (s *Server) automate() {
	for {
		time.Sleep(10 * time.Second)
		s.tickNotifications()
		cfg := s.st.LoadSettings()
		if cfg.Automations.PrintBoostMinutes > 0 && cfg.EWeLink.BoxPrint != "" {
			s.switchOnce(cfg.EWeLink.BoxPrint, s.bambu.PrintingOrBoost(cfg.Automations.PrintBoostMinutes))
		}
		if cfg.EWeLink.BoxAlways != "" {
			s.switchOnce(cfg.EWeLink.BoxAlways, cfg.Automations.BoxAlwaysOn)
		}
	}
}

func (s *Server) switchOnce(ref string, on bool) {
	s.mu.Lock()
	prev, seen := s.lastOn[ref]
	s.mu.Unlock()
	if seen && prev == on {
		return
	}
	if err := s.ew.Switch(ref, on); err != nil {
		log.Printf("automate switch %s: %v", ref, err)
		return
	}
	s.mu.Lock()
	s.lastOn[ref] = on
	s.mu.Unlock()
}

func withLog(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Security-Policy",
			"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com https://ezui.ys7.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob: https:; connect-src 'self' ws: wss: https:; worker-src 'self' blob:; media-src 'self' blob: https:; frame-ancestors 'none'; frame-src 'self' https://open.ys7.com")
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.Header().Set("Referrer-Policy", "no-referrer")
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %v", r.Method, r.URL.Path, time.Since(start))
	})
}

// verifyWeCom 校验企业微信回调的签名回包（echostr 解密后原样返回）。
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
