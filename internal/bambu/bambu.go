package bambu

import (
	"bytes"
	"crypto/tls"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strconv"
	"strings"
	"sync"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
)

type Client struct {
	mu       sync.RWMutex
	account  string
	password string
	region   string
	sn       string
	token    string
	userID   string
	mqtt     mqtt.Client
	mqttUser string
	snapshot map[string]any
	updated  time.Time
	err      string
	printEnd time.Time
	needCode bool
}

func New() *Client { return &Client{snapshot: map[string]any{}} }

func (c *Client) Configure(region, account, password, sn, token string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.region, c.account, c.password, c.sn = region, account, password, strings.TrimSpace(sn)
	if strings.TrimSpace(token) != "" {
		c.token = strings.TrimSpace(token)
		if u := jwtUsername(c.token); u != "" {
			c.userID, c.mqttUser = u, u
		}
	}
}

func (c *Client) Token() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.token
}

func (c *Client) UserID() string {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.userID
}

func (c *Client) Status() map[string]any {
	c.mu.RLock()
	defer c.mu.RUnlock()
	out := map[string]any{
		"configured":     (c.token != "" || (c.account != "" && c.password != "")) && c.sn != "",
		"connected":      c.mqtt != nil && c.mqtt.IsConnected(),
		"updated_at":     "",
		"error":          c.err,
		"printer_sn":     c.sn,
		"print_ended_at": nil,
		"need_code":      c.needCode,
		"has_token":      c.token != "",
		"mqtt_user":      redactUser(c.mqttUser),
	}
	if !c.updated.IsZero() {
		out["updated_at"] = c.updated.UTC().Format(time.RFC3339)
	}
	if !c.printEnd.IsZero() {
		out["print_ended_at"] = c.printEnd.UTC().Format(time.RFC3339)
	}
	gcode, _ := c.snapshot["gcode_state"].(string)
	stage := fmt.Sprint(c.snapshot["stage"])
	boost := PrintingFromState(gcode, stage) || (!c.printEnd.IsZero() && time.Since(c.printEnd) < 30*time.Minute)
	for k, v := range c.snapshot {
		out[k] = v
	}
	out["print_boost_active"] = boost
	return out
}

func (c *Client) HasPrintState() bool {
	c.mu.RLock()
	defer c.mu.RUnlock()
	if !c.printEnd.IsZero() || !c.updated.IsZero() {
		return true
	}
	return c.mqtt != nil && c.mqtt.IsConnected()
}

func (c *Client) PrintingOrBoost(minutes int) bool {
	c.mu.RLock()
	gcode, _ := c.snapshot["gcode_state"].(string)
	stage := fmt.Sprint(c.snapshot["stage"])
	end := c.printEnd
	c.mu.RUnlock()

	if PrintingFromState(gcode, stage) {
		return true
	}
	if minutes <= 0 {
		minutes = 30
	}
	return !end.IsZero() && time.Since(end) < time.Duration(minutes)*time.Minute
}

func PrintingFromState(gcode, stage string) bool {
	switch strings.ToUpper(strings.TrimSpace(gcode)) {
	case "RUNNING", "PREPARE", "SLICING", "PAUSE":
		return true
	case "FINISH", "FINISHED", "FAILED", "IDLE":
		return false
	}
	// After a job the printer often leaves mc_print_stage=0 ("printing").
	// Do not treat that leftover as an active print when gcode_state is unknown.
	switch strings.ToLower(strings.TrimSpace(stage)) {
	case "auto_bed_leveling", "heatbed_preheating", "changing_filament",
		"paused_filament_runout", "heating_hotend", "paused_user":
		return true
	}
	return false
}

func (c *Client) Reconnect() {
	c.mu.Lock()
	if c.mqtt != nil {
		c.mqtt.Disconnect(250)
		c.mqtt = nil
	}
	account, password, sn, region, token := c.account, c.password, c.sn, c.region, c.token
	c.mu.Unlock()
	if sn == "" {
		return
	}
	if token != "" {
		user := resolveMQTTUser(region, token)
		c.mu.Lock()
		c.userID = user
		c.mqttUser = user
		c.needCode = false
		c.err = ""
		c.mu.Unlock()
		c.startMQTT(region, sn)
		return
	}
	if account == "" || password == "" {
		return
	}
	need, err := c.loginPassword(region, account, password)
	if err != nil {
		c.mu.Lock()
		c.err = err.Error()
		c.mu.Unlock()
		return
	}
	if need {
		c.mu.Lock()
		c.needCode = true
		c.err = "拓竹要求验证码：先点「发送验证码」，手机/邮箱收到后填入再点「用验证码登录」"
		c.mu.Unlock()
		return
	}
	c.startMQTT(region, sn)
}

func (c *Client) SendCode() error {
	c.mu.RLock()
	account, region := c.account, c.region
	c.mu.RUnlock()
	if account == "" {
		return fmt.Errorf("先保存拓竹账号")
	}
	base := apiBase(region)
	var endpoint string
	var payload any
	if strings.Contains(account, "@") {
		endpoint = base + "/v1/user-service/user/sendemail/code"
		payload = map[string]string{"email": account, "type": "codeLogin"}
	} else if region == "" || region == "cn" {
		endpoint = "https://api.bambulab.cn/v1/user-service/user/sendsmscode"
		payload = map[string]string{"phone": account, "type": "codeLogin"}
	} else {
		endpoint = base + "/v1/user-service/user/sendsmscode"
		payload = map[string]string{"phone": account, "type": "codeLogin"}
	}
	raw, code, err := postJSON(endpoint, payload)
	if err != nil {
		return err
	}
	if code >= 400 {
		return fmt.Errorf("发送验证码失败(%d): %s", code, truncate(string(raw), 200))
	}
	return nil
}

func (c *Client) LoginWithCode(code string) error {
	c.mu.RLock()
	account, region, sn := c.account, c.region, c.sn
	c.mu.RUnlock()
	code = strings.TrimSpace(code)
	if account == "" || code == "" {
		return fmt.Errorf("账号和验证码都要填")
	}
	raw, status, err := postJSON(apiBase(region)+"/v1/user-service/user/login", map[string]string{
		"account": account, "code": code,
	})
	if err != nil {
		return err
	}
	if status >= 400 {
		return fmt.Errorf("验证码登录失败(%d): %s", status, truncate(string(raw), 200))
	}
	if err := c.applyLoginJSON(raw); err != nil {
		return err
	}
	c.mu.Lock()
	c.needCode = false
	c.mu.Unlock()
	if sn != "" {
		c.startMQTT(region, sn)
	}
	return nil
}

func (c *Client) ApplyToken(token string) error {
	token = strings.TrimSpace(token)
	if token == "" {
		return fmt.Errorf("token 为空")
	}
	c.mu.Lock()
	c.token = token
	region := c.region
	sn := c.sn
	c.mu.Unlock()
	user := resolveMQTTUser(region, token)
	c.mu.Lock()
	c.userID = user
	c.mqttUser = user
	c.needCode = false
	c.err = ""
	c.mu.Unlock()
	if sn != "" {
		c.startMQTT(region, sn)
	}
	return nil
}

func (c *Client) loginPassword(region, account, password string) (needCode bool, err error) {
	raw, status, err := postJSON(apiBase(region)+"/v1/user-service/user/login", map[string]string{
		"account": account, "password": password, "apiError": "",
	})
	if err != nil {
		return false, err
	}
	if status >= 400 {
		return false, fmt.Errorf("拓竹登录失败(%d): %s", status, truncate(string(raw), 200))
	}
	var parsed map[string]any
	_ = json.Unmarshal(raw, &parsed)
	loginType, _ := parsed["loginType"].(string)
	token, _ := parsed["accessToken"].(string)
	if loginType == "verifyCode" || token == "" {
		return true, nil
	}
	if loginType == "tfa" {
		return false, fmt.Errorf("该账号开了二次验证（tfa），请改用验证码或粘贴 Token")
	}
	return false, c.applyLoginJSON(raw)
}

func (c *Client) applyLoginJSON(raw []byte) error {
	var parsed map[string]any
	_ = json.Unmarshal(raw, &parsed)
	token, _ := parsed["accessToken"].(string)
	if token == "" {
		if data, ok := parsed["data"].(map[string]any); ok {
			token, _ = data["accessToken"].(string)
		}
	}
	if token == "" {
		return fmt.Errorf("登录成功但没有 accessToken: %s", truncate(string(raw), 200))
	}
	c.mu.Lock()
	c.token = token
	region := c.region
	c.mu.Unlock()
	user := resolveMQTTUser(region, token)
	c.mu.Lock()
	c.userID = user
	c.mqttUser = user
	c.err = ""
	c.mu.Unlock()
	return nil
}

func (c *Client) startMQTT(region, sn string) {
	c.mu.RLock()
	token, user := c.token, c.mqttUser
	c.mu.RUnlock()
	if token == "" {
		return
	}
	if user == "" {
		user = resolveMQTTUser(region, token)
		c.mu.Lock()
		c.mqttUser = user
		c.mu.Unlock()
	}
	if user == "" {
		c.mu.Lock()
		c.err = "无法从 token 解析 MQTT 用户名（需要 JWT 里的 username=u_数字）"
		c.mu.Unlock()
		return
	}
	host := "cn.mqtt.bambulab.com:8883"
	if region != "" && region != "cn" {
		host = "us.mqtt.bambulab.com:8883"
	}
	opts := mqtt.NewClientOptions()
	opts.AddBroker("ssl://" + host)
	opts.SetClientID(fmt.Sprintf("printpilot-%d", time.Now().UnixNano()%1e12))
	opts.SetUsername(user)
	opts.SetPassword(token)
	opts.SetProtocolVersion(4) // MQTT 3.1.1
	opts.SetCleanSession(true)
	opts.SetTLSConfig(&tls.Config{MinVersion: tls.VersionTLS12})
	opts.SetKeepAlive(30 * time.Second)
	opts.SetAutoReconnect(true)
	opts.SetConnectionLostHandler(func(_ mqtt.Client, err error) {
		c.mu.Lock()
		c.err = "mqtt: " + err.Error()
		c.mu.Unlock()
	})
	opts.SetOnConnectHandler(func(cli mqtt.Client) {
		topic := fmt.Sprintf("device/%s/report", sn)
		_ = cli.Subscribe(topic, 0, c.onMessage)
		req := fmt.Sprintf("device/%s/request", sn)
		_ = cli.Publish(req, 0, false, `{"pushing":{"sequence_id":"1","command":"pushall"}}`)
		_ = cli.Publish(req, 0, false, `{"info":{"sequence_id":"2","command":"get_version"}}`)
		c.mu.Lock()
		c.err = ""
		c.mu.Unlock()
	})
	cli := mqtt.NewClient(opts)
	if tok := cli.Connect(); tok.Wait() && tok.Error() != nil {
		c.mu.Lock()
		c.err = tok.Error().Error()
		c.mu.Unlock()
		return
	}
	c.mu.Lock()
	c.mqtt = cli
	c.mu.Unlock()
}

func (c *Client) onMessage(_ mqtt.Client, m mqtt.Message) {
	var raw map[string]any
	if err := json.Unmarshal(m.Payload(), &raw); err != nil {
		return
	}
	print := map[string]any{}
	if p, ok := raw["print"].(map[string]any); ok {
		print = p
	}
	if len(print) == 0 {
		return
	}
	c.applyPrint(print)
}

func (c *Client) applyPrint(print map[string]any) {
	c.mu.Lock()
	defer c.mu.Unlock()
	if c.snapshot == nil {
		c.snapshot = map[string]any{}
	}
	prev, _ := c.snapshot["gcode_state"].(string)
	merge := func(key string, v any) {
		if v == nil {
			return
		}
		if s, ok := v.(string); ok && s == "" {
			return
		}
		c.snapshot[key] = v
	}
	merge("nozzle_temp", first(print, "nozzle_temper", "nozzle_temp"))
	merge("nozzle_target", first(print, "nozzle_target_temper", "nozzle_target_temp"))
	merge("bed_temp", first(print, "bed_temper", "bed_temp"))
	merge("bed_target", first(print, "bed_target_temper", "bed_target_temp"))
	merge("layer", first(print, "layer_num", "mc_print_layer"))
	merge("total_layer", first(print, "total_layer_num", "mc_print_sub_layer"))
	merge("progress", first(print, "mc_percent", "percent"))
	merge("remaining", first(print, "mc_remaining_time", "remain_time"))
	merge("spd_mag", first(print, "spd_mag"))
	merge("spd_lvl", first(print, "spd_lvl"))
	merge("fan_gear", first(print, "cooling_fan_speed"))
	if st := first(print, "mc_print_stage", "print_stage"); st != nil {
		merge("stage", stageName(st))
	}
	merge("gcode_state", print["gcode_state"])
	merge("subtask", first(print, "subtask_name", "task_name", "gcode_file"))
	if vt, ok := print["vt_tray"].(map[string]any); ok {
		merge("vt_tray", vt)
	}
	if ams, ok := print["ams"].(map[string]any); ok {
		merge("ams", ams)
		if tn := first(ams, "tray_now"); tn != nil {
			merge("tray_now", tn)
		}
	}
	if tn := first(print, "tray_now", "ams_tray_now"); tn != nil {
		merge("tray_now", tn)
	}
	c.updated = time.Now()
	cur, _ := c.snapshot["gcode_state"].(string)
	if isActiveGcode(cur) {
		c.printEnd = time.Time{}
	} else if c.printEnd.IsZero() && isEndedGcode(cur) && (isActiveGcode(prev) || (prev != "" && !strings.EqualFold(prev, cur))) {
		c.printEnd = time.Now()
	}
}

func isActiveGcode(s string) bool {
	switch strings.ToUpper(strings.TrimSpace(s)) {
	case "RUNNING", "PREPARE", "SLICING", "PAUSE":
		return true
	}
	return false
}

func isEndedGcode(s string) bool {
	switch strings.ToUpper(strings.TrimSpace(s)) {
	case "FINISH", "FINISHED", "FAILED", "IDLE":
		return true
	}
	return false
}

func first(m map[string]any, keys ...string) any {
	for _, k := range keys {
		if v, ok := m[k]; ok && v != nil {
			return v
		}
	}
	return nil
}

func stageName(v any) any {
	var n int
	switch t := v.(type) {
	case float64:
		n = int(t)
	case json.Number:
		i, _ := t.Int64()
		n = int(i)
	case string:
		if t != "" {
			return t
		}
		return v
	default:
		return v
	}
	if name, ok := printStages[n]; ok {
		return name
	}
	return n
}

var printStages = map[int]string{
	-1: "idle", 0: "printing", 1: "auto_bed_leveling", 2: "heatbed_preheating",
	4: "changing_filament", 6: "paused_filament_runout", 7: "heating_hotend",
	16: "paused_user", 255: "idle",
}

func resolveMQTTUser(region, token string) string {
	if u := jwtUsername(token); u != "" {
		return u
	}
	if uid := fetchPreferenceUID(region, token); uid != "" {
		if strings.HasPrefix(uid, "u_") {
			return uid
		}
		return "u_" + uid
	}
	return ""
}

func jwtUsername(token string) string {
	parts := strings.Split(token, ".")
	if len(parts) < 2 {
		return ""
	}
	seg := parts[1]
	if m := len(seg) % 4; m != 0 {
		seg += strings.Repeat("=", 4-m)
	}
	b, err := base64.URLEncoding.DecodeString(seg)
	if err != nil {
		b, err = base64.StdEncoding.DecodeString(seg)
		if err != nil {
			return ""
		}
	}
	dec := json.NewDecoder(bytes.NewReader(b))
	dec.UseNumber()
	var m map[string]any
	if dec.Decode(&m) != nil {
		return ""
	}
	if u := asMQTTUser(m["username"]); u != "" {
		return u
	}
	for _, k := range []string{"user_id", "userId", "uid"} {
		if u := asMQTTUser(m[k]); u != "" {
			return u
		}
	}
	return ""
}

func asMQTTUser(v any) string {
	if v == nil {
		return ""
	}
	var s string
	switch t := v.(type) {
	case string:
		s = strings.TrimSpace(t)
	case json.Number:
		s = t.String()
	case float64:
		s = strconv.FormatInt(int64(t), 10)
	case int64:
		s = strconv.FormatInt(t, 10)
	case int:
		s = strconv.Itoa(t)
	default:
		return ""
	}
	s = strings.TrimPrefix(s, "u_")
	if s == "" {
		return ""
	}
	for _, r := range s {
		if r < '0' || r > '9' {
			return ""
		}
	}
	return "u_" + s
}

func fetchPreferenceUID(region, token string) string {
	base := apiBase(region)
	urls := []string{
		base + "/v1/design-user-service/my/preference",
		base + "/v1/user-service/my/preference",
		base + "/v1/iot-service/api/user/bind",
	}
	for _, u := range urls {
		req, _ := http.NewRequest(http.MethodGet, u, nil)
		for k, v := range slicerHeaders() {
			req.Header.Set(k, v)
		}
		req.Header.Set("Authorization", "Bearer "+token)
		res, err := http.DefaultClient.Do(req)
		if err != nil {
			continue
		}
		raw, _ := io.ReadAll(res.Body)
		res.Body.Close()
		if res.StatusCode >= 400 {
			continue
		}
		dec := json.NewDecoder(bytes.NewReader(raw))
		dec.UseNumber()
		var parsed map[string]any
		if dec.Decode(&parsed) != nil {
			continue
		}
		if u := asMQTTUser(parsed["uid"]); u != "" {
			return u
		}
		if u := asMQTTUser(parsed["username"]); u != "" {
			return u
		}
		if data, ok := parsed["data"].(map[string]any); ok {
			if u := asMQTTUser(data["uid"]); u != "" {
				return u
			}
			if u := asMQTTUser(data["username"]); u != "" {
				return u
			}
		}
	}
	return ""
}

func slicerHeaders() map[string]string {
	return map[string]string{
		"User-Agent":           "bambu_network_agent/01.09.05.01",
		"X-BBL-Client-Name":    "OrcaSlicer",
		"X-BBL-Client-Type":    "slicer",
		"X-BBL-Client-Version": "01.09.05.51",
		"X-BBL-Language":       "zh-CN",
		"X-BBL-OS-Type":        "linux",
		"Accept":               "application/json",
		"Content-Type":         "application/json",
	}
}

func redactUser(u string) string {
	if len(u) <= 5 {
		return u
	}
	return u[:5] + "***"
}

func apiBase(region string) string {
	if region != "" && region != "cn" {
		return "https://api.bambulab.com"
	}
	return "https://api.bambulab.cn"
}

func postJSON(url string, payload any) ([]byte, int, error) {
	body, _ := json.Marshal(payload)
	req, _ := http.NewRequest(http.MethodPost, url, bytes.NewReader(body))
	for k, v := range slicerHeaders() {
		req.Header.Set(k, v)
	}
	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, 0, err
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	return raw, res.StatusCode, nil
}

func num(v any) any {
	switch t := v.(type) {
	case float64, int, int64, json.Number, string:
		return t
	default:
		return v
	}
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}




// SetFilament is added for testing MQTT filament assignment
func (c *Client) SetFilament(amsId int, trayId int, infoIdx string, color string, matType string) error {
	c.mu.RLock()
	cli := c.mqtt
	sn := c.sn
	c.mu.RUnlock()
	if cli == nil {
		return fmt.Errorf("mqtt not connected")
	}
	topic := fmt.Sprintf("device/%s/request", sn)
	payload := fmt.Sprintf(`{"print":{"sequence_id":"999","command":"ami_assign_info","ams_id":%d,"tray_id":%d,"tray_info_idx":"%s","tray_color":"%s","nozzle_temp_min":230,"nozzle_temp_max":260,"tray_type":"%s"}}`, amsId, trayId, infoIdx, color, matType)
	tok := cli.Publish(topic, 0, false, payload)
	tok.Wait()
	return tok.Error()
}
