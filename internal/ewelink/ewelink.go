package ewelink

import (
	"bytes"
	"crypto/hmac"
	"crypto/md5"
	"crypto/rand"
	"crypto/sha256"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"
	"unicode"
)

// Public CoolKit app credentials used by unofficial clients.
// Developer-center APPID is OAuth-only and returns 407 on /v2/user/login.
// Prefer the SonoffLAN/HA pair — it still allows password login.
var communityApps = [][2]string{
	{"R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv", "1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru"},
	{"Uw83EKZFxdif7XFXEsrpduz5YyjP7nTl", "mXLOjea0woSMvK9gw7Fjsy7YlFO4iSu6"},
	{"4s1FXKC9FaGfoqXhmXSJneb3qcm1gOak", "oKvCM6ooyrX8Jk4d"},
	{"KOBxGJna5qkk3JLXw3LHLX3wSNiPjAVi", "4v0sv6X5IM2ASIBiNDj6kGmSfxo40w7n"},
}

const (
	DefaultAppID     = "R8Oq3y0eSZSYdKccHlrQzT1ACCOUT9Gv"
	DefaultAppSecret = "1ve5Qk9GXfUhKAn1svnKwpAlxXkMarru"
)

type Client struct {
	mu     sync.Mutex
	token  string
	rt     string
	apiKey string
	host   string
	err    string
	cfg    Config
	// token 刷新后回调（server 层用它落库），由 New 后设置一次。
	onRefresh func(at, rt string)
	http      *http.Client
}

// coolkit API 偶发不回包，没有超时会挂死调用方（machine/automate 轮询）。
var httpClient = &http.Client{Timeout: 15 * time.Second}

type Config struct {
	Region, Account, Password, AppID, AppSecret string
	AccessToken, RefreshToken                   string
}

func New() *Client { return &Client{} }

func (c *Client) OnTokenRefresh(f func(at, rt string)) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.onRefresh = f
}

func (c *Client) notifyRefresh() {
	c.mu.Lock()
	f, at, rt := c.onRefresh, c.token, c.rt
	c.mu.Unlock()
	if f != nil && at != "" {
		f(at, rt)
	}
}

func (c *Client) Configure(cfg Config) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.cfg = cfg
	if c.cfg.AppID == "" {
		c.cfg.AppID = DefaultAppID
	}
	if c.cfg.AppSecret == "" {
		c.cfg.AppSecret = DefaultAppSecret
	}
	c.host = hostFor(c.cfg.Region)
	if cfg.AccessToken != "" {
		c.token = cfg.AccessToken
	}
	if cfg.RefreshToken != "" {
		c.rt = cfg.RefreshToken
	}
	c.err = ""
}

func hostFor(region string) string {
	r := strings.ToLower(strings.TrimSpace(region))
	switch r {
	case "", "cn", "china", "中国", "国内", "prc":
		return "https://cn-apia.coolkit.cn"
	case "as", "hk", "sg", "ap", "asia":
		return "https://as-apia.coolkit.cc"
	case "us", "usa", "america":
		return "https://us-apia.coolkit.cc"
	case "eu", "europe":
		return "https://eu-apia.coolkit.cc"
	default:
		// Unknown text used to fall through to EU and 407 on CN accounts.
		return "https://cn-apia.coolkit.cn"
	}
}

func (c *Client) Status() map[string]any {
	c.mu.Lock()
	defer c.mu.Unlock()
	return map[string]any{
		"configured":   c.cfg.Account != "" && (c.cfg.Password != "" || c.token != ""),
		"logged_in":    c.token != "",
		"has_password": c.cfg.Password != "",
		"has_token":    c.token != "",
		"error":        c.err,
	}
}

func (c *Client) Tokens() (at, rt string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.token, c.rt
}

func (c *Client) Login() error {
	c.mu.Lock()
	cfg := c.cfg
	c.mu.Unlock()
	if cfg.Account == "" || cfg.Password == "" {
		if cfg.AccessToken != "" {
			c.mu.Lock()
			c.token = cfg.AccessToken
			c.rt = cfg.RefreshToken
			c.err = ""
			c.mu.Unlock()
			return nil
		}
		return fmt.Errorf("未填写易微联账号或密码")
	}

	apps := communityApps
	if cfg.AppID != "" && cfg.AppSecret != "" && !isCommunity(cfg.AppID) {
		// Try the user-supplied pair first, then fall back. Official
		// developer APPID returns 407 on password login.
		apps = append([][2]string{{cfg.AppID, cfg.AppSecret}}, communityApps...)
	}

	var last error
	passwords := []string{cfg.Password, md5Hex(cfg.Password)}
	for _, app := range apps {
		for _, pw := range passwords {
			if err := c.loginOnce(cfg.Account, pw, cfg.Region, app[0], app[1]); err != nil {
				last = err
				if isCode(err, 407) {
					break // this APPID cannot do password login
				}
				continue
			}
			return nil
		}
	}
	if last == nil {
		last = fmt.Errorf("易微联登录失败")
	}
	if isCode(last, 407) {
		last = fmt.Errorf("易微联登录失败(407): 当前 APPID 不允许账号密码登录。请把设置里的 APPID/SECRET 留空后重试；或从 web.ewelink.cc 登录后把 Access Token 粘贴进来")
	}
	c.mu.Lock()
	c.err = last.Error()
	c.mu.Unlock()
	return last
}

func (c *Client) ApplyToken(at string) error {
	at = strings.TrimSpace(at)
	at = strings.TrimPrefix(at, "Bearer ")
	at = strings.Trim(at, "\"'")
	if at == "" {
		return fmt.Errorf("token 是空的")
	}
	c.mu.Lock()
	c.token = at
	c.err = ""
	if c.cfg.AppID == "" || isCommunity(c.cfg.AppID) {
		c.cfg.AppID = DefaultAppID
		c.cfg.AppSecret = DefaultAppSecret
	}
	c.mu.Unlock()
	if _, err := c.Devices(); err != nil {
		// Token from the official web app may need another X-CK-Appid.
		for _, app := range communityApps {
			c.mu.Lock()
			c.cfg.AppID, c.cfg.AppSecret, c.token = app[0], app[1], at
			c.mu.Unlock()
			if _, err2 := c.Devices(); err2 == nil {
				c.notifyRefresh()
				return nil
			}
		}
		c.mu.Lock()
		c.token = ""
		c.err = err.Error()
		c.mu.Unlock()
		return err
	}
	c.notifyRefresh()
	return nil
}

func (c *Client) loginOnce(account, password, region, appID, appSecret string) error {
	payload := map[string]any{
		"password":    password,
		"countryCode": "+86",
	}
	if strings.Contains(account, "@") {
		payload["email"] = strings.TrimSpace(account)
	} else {
		payload["phoneNumber"] = normalizePhone(account)
	}
	host := hostFor(region)
	body, err := c.postLogin(host, appID, appSecret, payload)
	if err != nil {
		return err
	}
	parsed, raw := parseLogin(body)
	// 10004 = account lives in another region. Retry once on that host.
	if parsed.Error == 10004 && parsed.Data.Region != "" {
		host = hostFor(parsed.Data.Region)
		body, err = c.postLogin(host, appID, appSecret, payload)
		if err != nil {
			return err
		}
		parsed, raw = parseLogin(body)
	}
	if parsed.Error != 0 || parsed.Data.At == "" {
		return fmt.Errorf("%s", loginErr(parsed.Error, parsed.Msg, raw))
	}
	c.mu.Lock()
	c.token = parsed.Data.At
	c.rt = parsed.Data.Rt
	c.apiKey = parsed.Data.APIKey
	if parsed.Data.User.APIKey != "" {
		c.apiKey = parsed.Data.User.APIKey
	}
	c.cfg.AppID = appID
	c.cfg.AppSecret = appSecret
	if parsed.Data.Region != "" {
		c.cfg.Region = parsed.Data.Region
	}
	c.host = host
	c.err = ""
	c.mu.Unlock()
	c.notifyRefresh()
	return nil
}

func (c *Client) postLogin(host, appID, appSecret string, payload map[string]any) ([]byte, error) {
	raw, _ := json.Marshal(payload)
	req, _ := http.NewRequest(http.MethodPost, host+"/v2/user/login", bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("X-CK-Appid", appID)
	req.Header.Set("X-CK-Nonce", nonce(8))
	req.Header.Set("Authorization", "Sign "+sign(raw, appSecret))
	res, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	return io.ReadAll(res.Body)
}

type loginResp struct {
	Error int    `json:"error"`
	Msg   string `json:"msg"`
	Data  struct {
		At     string `json:"at"`
		Rt     string `json:"rt"`
		APIKey string `json:"apikey"`
		Region string `json:"region"`
		User   struct {
			APIKey string `json:"apikey"`
		} `json:"user"`
	} `json:"data"`
}

func parseLogin(body []byte) (loginResp, string) {
	var parsed loginResp
	_ = json.Unmarshal(body, &parsed)
	return parsed, string(body)
}

func loginErr(code int, msg, raw string) string {
	hint := map[int]string{
		10001: "登录已过期，重新填一次密码",
		10003: "账号不存在，确认是易微联 App 里那一套手机号/邮箱",
		10004: "账号不在当前地区，已自动改区重试仍失败",
		10005: "密码不对",
		10014: "账号或密码不对",
		407:   "这个 APPID 不允许账号密码登录",
		401:   "签名失败，检查 APPSECRET 或把高级项留空",
		400:   "请求参数不对，手机号请填 11 位或带 +86",
	}
	if h, ok := hint[code]; ok {
		return fmt.Sprintf("易微联登录失败(%d): %s", code, h)
	}
	if msg != "" {
		return fmt.Sprintf("易微联登录失败(%d): %s", code, msg)
	}
	return fmt.Sprintf("易微联登录失败(%d): %s", code, truncate(raw, 200))
}

// Channel is one controllable outlet. A 三联继电器 becomes three rows.
type Channel struct {
	ID       string `json:"id"`
	DeviceID string `json:"device_id"`
	Outlet   *int   `json:"outlet"`
	Name     string `json:"name"`
	Online   bool   `json:"online"`
	On       *bool  `json:"on"`
	UIID     int    `json:"uiid"`
	Model    string `json:"model"`
	Channels int    `json:"channels"`
}

func (c *Client) Devices() ([]Channel, error) {
	if err := c.ensure(); err != nil {
		return nil, err
	}
	c.mu.Lock()
	host, token, appid := c.host, c.token, c.cfg.AppID
	c.mu.Unlock()
	req, _ := http.NewRequest(http.MethodGet, host+"/v2/device/thing?num=0", nil)
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-CK-Appid", appid)
	res, err := httpClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)
	var parsed struct {
		Error int    `json:"error"`
		Msg   string `json:"msg"`
		Data  struct {
			ThingList []struct {
				ItemType int            `json:"itemType"`
				ItemData map[string]any `json:"itemData"`
			} `json:"thingList"`
		} `json:"data"`
	}
	_ = json.Unmarshal(body, &parsed)
	if parsed.Error == 401 || parsed.Error == 406 || parsed.Error == 10001 {
		c.mu.Lock()
		c.token = ""
		c.mu.Unlock()
		if err := c.Login(); err != nil {
			return nil, err
		}
		return c.Devices()
	}
	if parsed.Error != 0 {
		return nil, fmt.Errorf("拉取设备失败(%d): %s", parsed.Error, firstNonEmpty(parsed.Msg, truncate(string(body), 200)))
	}
	var out []Channel
	for _, it := range parsed.Data.ThingList {
		out = append(out, expandDevice(it.ItemData)...)
	}
	return out, nil
}

func expandDevice(item map[string]any) []Channel {
	id := str(item["deviceid"])
	if id == "" {
		return nil
	}
	name := str(item["name"])
	if name == "" {
		name = id
	}
	online, _ := item["online"].(bool)
	uiid := asInt(deep(item, "extra", "uiid"))
	if uiid == 0 {
		uiid = asInt(item["uiid"])
	}
	model := str(item["productModel"])
	params, _ := item["params"].(map[string]any)
	if params == nil {
		params = map[string]any{}
	}
	chNames := channelNames(item)
	n := channelCount(uiid, params)
	if n <= 1 {
		on := switchOn(params, -1)
		return []Channel{{
			ID: id, DeviceID: id, Name: name, Online: online, On: on,
			UIID: uiid, Model: model, Channels: 1,
		}}
	}
	var out []Channel
	for i := 0; i < n; i++ {
		outlet := i
		label := fmt.Sprintf("%s · 通道%d", name, i+1)
		if extra := chNames[strconv.Itoa(i)]; extra != "" {
			label += " " + extra
		}
		on := switchOn(params, i)
		out = append(out, Channel{
			ID: fmt.Sprintf("%s:%d", id, i), DeviceID: id, Outlet: &outlet,
			Name: label, Online: online, On: on, UIID: uiid, Model: model, Channels: n,
		})
	}
	return out
}

func channelNames(item map[string]any) map[string]string {
	out := map[string]string{}
	tags, _ := item["tags"].(map[string]any)
	if tags == nil {
		return out
	}
	for _, key := range []string{"ck_channel_name", "channelName"} {
		raw, ok := tags[key]
		if !ok {
			continue
		}
		switch t := raw.(type) {
		case map[string]any:
			for k, v := range t {
				if s := str(v); s != "" {
					out[k] = s
				}
			}
		case string:
			var m map[string]any
			if json.Unmarshal([]byte(t), &m) == nil {
				for k, v := range m {
					if s := str(v); s != "" {
						out[k] = s
					}
				}
			}
		}
	}
	return out
}

func channelCount(uiid int, params map[string]any) int {
	if raw, ok := params["switches"].([]any); ok && len(raw) > 0 {
		return len(raw)
	}
	switch uiid {
	case 2, 3, 4:
		return uiid
	case 7:
		return 2
	case 8:
		return 3
	case 9:
		return 4
	case 126, 165:
		return 2
	case 161, 162, 163:
		return uiid - 160
	case 174:
		return 1
	case 175:
		return 2
	case 176:
		return 3
	case 177:
		return 4
	default:
		return 1
	}
}

func switchOn(params map[string]any, outlet int) *bool {
	if outlet < 0 {
		if s := str(params["switch"]); s == "on" || s == "off" {
			v := s == "on"
			return &v
		}
		return nil
	}
	raw, ok := params["switches"].([]any)
	if !ok {
		return nil
	}
	for _, it := range raw {
		m, _ := it.(map[string]any)
		if m == nil {
			continue
		}
		if asInt(m["outlet"]) == outlet {
			if s := str(m["switch"]); s == "on" || s == "off" {
				v := s == "on"
				return &v
			}
		}
	}
	return nil
}

func (c *Client) Switch(ref string, on bool) error {
	deviceID, outlet, err := parseRef(ref)
	if err != nil {
		return err
	}
	if err := c.ensure(); err != nil {
		return err
	}
	c.mu.Lock()
	host, token, appid := c.host, c.token, c.cfg.AppID
	c.mu.Unlock()
	state := "off"
	if on {
		state = "on"
	}
	var params map[string]any
	if outlet == nil {
		params = map[string]any{"switch": state}
	} else {
		params = map[string]any{
			"switches": []map[string]any{{"outlet": *outlet, "switch": state}},
		}
	}
	payload := map[string]any{"type": 1, "id": deviceID, "params": params}
	raw, _ := json.Marshal(payload)
	req, _ := http.NewRequest(http.MethodPost, host+"/v2/device/thing/status", bytes.NewReader(raw))
	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("X-CK-Appid", appid)
	res, err := httpClient.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	body, _ := io.ReadAll(res.Body)
	var parsed struct {
		Error int    `json:"error"`
		Msg   string `json:"msg"`
	}
	_ = json.Unmarshal(body, &parsed)
	if parsed.Error == 401 || parsed.Error == 406 || parsed.Error == 10001 {
		c.mu.Lock()
		c.token = ""
		c.mu.Unlock()
		if err := c.Login(); err != nil {
			return err
		}
		return c.Switch(ref, on)
	}
	if parsed.Error != 0 {
		return fmt.Errorf("开关失败(%d): %s", parsed.Error, firstNonEmpty(parsed.Msg, truncate(string(body), 200)))
	}
	return nil
}

func parseRef(ref string) (string, *int, error) {
	ref = strings.TrimSpace(ref)
	if ref == "" {
		return "", nil, fmt.Errorf("未绑定设备")
	}
	id, rest, ok := strings.Cut(ref, ":")
	if !ok {
		return ref, nil, nil
	}
	n, err := strconv.Atoi(rest)
	if err != nil || n < 0 || n > 15 {
		return "", nil, fmt.Errorf("通道编号不对: %s（三联请用 deviceid:0 / :1 / :2）", ref)
	}
	return id, &n, nil
}

func (c *Client) ensure() error {
	c.mu.Lock()
	ok := c.token != ""
	c.mu.Unlock()
	if ok {
		return nil
	}
	return c.Login()
}

func md5Hex(s string) string {
	sum := md5.Sum([]byte(s))
	return hex.EncodeToString(sum[:])
}

func isCommunity(appID string) bool {
	for _, a := range communityApps {
		if a[0] == appID {
			return true
		}
	}
	return appID == ""
}

func isCode(err error, code int) bool {
	if err == nil {
		return false
	}
	return strings.Contains(err.Error(), fmt.Sprintf("(%d)", code))
}

func sign(body []byte, secret string) string {
	mac := hmac.New(sha256.New, []byte(secret))
	mac.Write(body)
	return base64.StdEncoding.EncodeToString(mac.Sum(nil))
}

func nonce(n int) string {
	const letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	b := make([]byte, n)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("%08x", time.Now().UnixNano())[:n]
	}
	for i := range b {
		b[i] = letters[int(b[i])%len(letters)]
	}
	return string(b)
}

func normalizePhone(s string) string {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "+") {
		return s
	}
	var digits strings.Builder
	for _, r := range s {
		if unicode.IsDigit(r) {
			digits.WriteRune(r)
		}
	}
	d := digits.String()
	if strings.HasPrefix(d, "86") && len(d) >= 13 {
		return "+" + d
	}
	if len(d) == 11 && strings.HasPrefix(d, "1") {
		return "+86" + d
	}
	if d != "" {
		return "+" + d
	}
	return s
}

func asInt(v any) int {
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case int64:
		return int(t)
	case json.Number:
		n, _ := t.Int64()
		return int(n)
	case string:
		n, _ := strconv.Atoi(t)
		return n
	default:
		return 0
	}
}

func str(v any) string {
	switch t := v.(type) {
	case string:
		return t
	case fmt.Stringer:
		return t.String()
	case float64:
		if t == float64(int64(t)) {
			return strconv.FormatInt(int64(t), 10)
		}
		return strconv.FormatFloat(t, 'f', -1, 64)
	default:
		return ""
	}
}

func deep(m map[string]any, keys ...string) any {
	var cur any = m
	for _, k := range keys {
		obj, ok := cur.(map[string]any)
		if !ok {
			return nil
		}
		cur = obj[k]
	}
	return cur
}

func firstNonEmpty(a, b string) string {
	if strings.TrimSpace(a) != "" {
		return a
	}
	return b
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
