package server

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"

	"pandaspool/internal/store"
)

// 打印异常监控：每 20 分钟抓一张萤石快照，与上一张对比后交给视觉模型
// （设置页「AI 视觉识别配置」的 Endpoint/Key/Model，OpenAI 兼容格式，
// 如 DeepSeek deepseek-flash——图像理解走 image_url / base64 data URL），
// 判断是否出现打印异常；异常时推企业微信（含抓拍图）。打印机空闲时只刷新基线。

const monitorInterval = 20 * time.Minute

type monitorResult struct {
	At      time.Time `json:"at"`
	Anomaly bool      `json:"anomaly"`
	Level   string    `json:"level"`
	Desc    string    `json:"desc"`
	Skipped string    `json:"skipped,omitempty"`
	Raw     string    `json:"raw,omitempty"`
}

func buildMonitorPrompt(rot string) string {
	rotDesc := "受封箱内部安装空间限制，摄像头本体侧置固定安装（画面具有固定的约 90 度侧转角度：画面左侧为热床及打印板，呈竖向纵深延伸；画面上方为机身前部与触摸屏；画面右侧为打印机底座与 Z 轴立柱）。"
	switch strings.TrimSpace(rot) {
	case "0":
		rotDesc = "摄像头固定安装在封箱内正向机位。"
	case "180":
		rotDesc = "摄像头为倒装吊顶安装（画面呈 180 度倒置）。"
	case "-90":
		rotDesc = "摄像头本体向左侧置固定安装（画面呈向左 90 度侧转）。"
	}

	return fmt.Sprintf(`你是 3D 打印机的视觉监控助手。下面是同一个监控摄像头在约 20 分钟间隔拍摄的两张快照（第一张较早，第二张较晚），打印机为拓竹 Bambu Lab A1，当前正在进行打印任务。

【监控机位与构图说明（非常重要）】：
1. 摄像头安装位置：固定安装在打印机封闭机箱（封箱）内部，处于机身前右上方侧俯视机位，镜头固定朝向拓竹 A1。
2. 画面物理旋转特征：%s
3. 动态机构正常位移说明：
   - 拓竹 A1 为卧式平台打印机（Bed-slinger），打印过程中热床沿 Y 轴前后滑动平移、喷头在横梁上左右移动均属于完全正常的机械运动。
   - 侧置视角和构图为摄像头的固定基准朝向，严禁将画面的侧向旋转构图、或热床/喷头的正常打印移动误判为“打印机被移动”、“摄像头被转向”或“机身倾倒”。

【需要判定的异常情形】：
请重点对比两张图片中热床表面正在打印的“模型本体”，判断是否发生以下严重打印故障：
- 乱丝 / 吐丝大量堆积（Spaghetti 炒面故障）
- 模型完全从热床脱落移位、倾倒或严重翘边掀起
- 打印件悬空失控、层间严重断裂错位
- 封箱内出现烟雾或明火险情

【正常现象（必须判定为无异常）】：
- 模型随着打印进度正常逐层增高、体积增加
- 热床和喷嘴在不同工位之间的正常位置切换
- 耗材挤出微小粗细纹理变化、夜视/补光灯光照反射变化
- 摄像头固有视角的静止背景

严格输出且仅输出一个合法 JSON 对象，不要包含 markdown 标记，格式如下：
{"anomaly": false, "level": "none", "desc": "一句简短中文描述"}
anomaly 为 true 时 level 用 warn 或 critical，desc 写明异常类型与位置；无异常时 level 用 none。`, rotDesc)
}

func (s *Server) monitorSetResult(r *monitorResult) {
	s.monitorMu.Lock()
	s.monitorLast = r
	s.monitorMu.Unlock()
}

func (s *Server) monitorSetSnapshot(jpeg []byte) {
	s.monitorMu.Lock()
	s.monitorPrev = jpeg
	s.monitorPrevAt = time.Now()
	s.monitorMu.Unlock()
}

// monitorTick 执行一次监控周期：抓拍 -> 与上一张对比（打印中才调用视觉）->
// 异常推企业微信（附抓拍图）。非打印时间不抓拍、不对比、不发给大模型。
func (s *Server) monitorTick() {
	// 只在打印中生效：非打印时间不抓拍、不对比、不发给大模型，并重置基线快照
	if !s.bambu.IsPrinting() {
		s.monitorMu.Lock()
		s.monitorPrev = nil
		s.monitorMu.Unlock()
		return
	}

	s.monitorMu.Lock()
	prev := s.monitorPrev
	prevAge := time.Since(s.monitorPrevAt)
	s.monitorMu.Unlock()

	cur, curURL, err := s.ezvizCaptureJPEG()
	if err != nil {
		s.monitorSetResult(&monitorResult{At: time.Now(), Skipped: "抓拍失败: " + err.Error()})
		log.Printf("[monitor] 抓拍失败: %v", err)
		return
	}
	s.monitorSetSnapshot(cur)

	if len(prev) == 0 || prevAge > 40*time.Minute {
		log.Printf("[monitor] 已建立/刷新基线快照 %dB（基线年龄 %s）", len(cur), prevAge.Round(time.Second))
		s.monitorSetResult(&monitorResult{At: time.Now(), Desc: "已建立基线快照", Skipped: "baseline"})
		return
	}

	anomaly, level, desc, raw, err := s.visionCompareMonitor(prev, cur)
	if err != nil {
		s.monitorSetResult(&monitorResult{At: time.Now(), Skipped: "视觉调用失败: " + err.Error()})
		log.Printf("[monitor] 视觉调用失败: %v", err)
		return
	}
	s.monitorSetResult(&monitorResult{At: time.Now(), Anomaly: anomaly, Level: level, Desc: desc, Raw: raw})
	log.Printf("[monitor] 对比完成: anomaly=%v level=%s desc=%s", anomaly, level, desc)
	if anomaly {
		cfg := s.st.LoadSettings()
		title := "⚠️ 打印异常监控告警（" + level + "）"
		pushDesc := desc + "\n\n（A1 摄像头 20 分钟对比监控）"
		go func() {
			if perr := s.weComNewsPush(&cfg, title, pushDesc, curURL); perr != nil {
				log.Printf("[monitor] WeCom 告警推送失败: %v", perr)
			}
		}()
	}
}

// printMonitorLoop 每 20 分钟一个监控周期；启动后先等 90 秒（等网络与
// 萤石凭证就绪），首轮只建基线。
func (s *Server) printMonitorLoop() {
	time.Sleep(90 * time.Second)
	s.monitorTick()
	for {
		time.Sleep(monitorInterval)
		s.monitorTick()
	}
}

// monitorLastHandler GET /api/monitor/last — 最近一次监控结果。
func (s *Server) monitorLastHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	s.monitorMu.Lock()
	last := s.monitorLast
	s.monitorMu.Unlock()
	if last == nil {
		w.Write([]byte(`{"ok":false,"hint":"监控尚未运行"}`))
		return
	}
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "result": last})
}

// monitorTestHandler POST /api/monitor/test — 立即抓拍并走一次视觉对比
// （设置页测试按钮；首轮只建基线并提示再点一次）。
func (s *Server) monitorTestHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	cur, _, err := s.ezvizCaptureJPEG()
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"ok": false, "error": "capture_failed", "hint": err.Error()})
		return
	}
	s.monitorMu.Lock()
	prev := s.monitorPrev
	s.monitorMu.Unlock()
	if len(prev) == 0 {
		s.monitorMu.Lock()
		s.monitorPrev = cur
		s.monitorPrevAt = time.Now()
		s.monitorMu.Unlock()
		json.NewEncoder(w).Encode(map[string]any{
			"ok":    false,
			"error": "baseline",
			"hint":  "已抓拍基线快照；再次点击即进行两图对比识别",
		})
		return
	}
	anomaly, level, desc, raw, err := s.visionCompareMonitor(prev, cur)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{"ok": false, "error": "ai_call_failed", "hint": err.Error()})
		return
	}
	s.monitorMu.Lock()
	s.monitorPrev = cur
	s.monitorLast = &monitorResult{At: time.Now(), Anomaly: anomaly, Level: level, Desc: desc, Raw: raw}
	s.monitorMu.Unlock()
	json.NewEncoder(w).Encode(map[string]any{
		"ok":      true,
		"anomaly": anomaly,
		"level":   level,
		"desc":    desc,
	})
}

// weComNewsPush 发企业微信通知：带 picUrl 时用 news 卡片（含配图），否则退回 textcard。
func (s *Server) weComNewsPush(cfg *store.Settings, title, desc, picUrl string) error {
	token, err := s.weComAccessToken(*cfg)
	if err != nil {
		return err
	}
	agentId := 1
	fmt.Sscanf(cfg.Automations.WeComAgentID, "%d", &agentId)
	toUser := "@all"
	if cfg.Automations.WeComToUser != "" {
		toUser = cfg.Automations.WeComToUser
	}
	var payload map[string]any
	if picUrl != "" {
		payload = map[string]any{
			"touser":  toUser,
			"msgtype": "news",
			"agentid": agentId,
			"news": map[string]any{
				"articles": []map[string]any{
					{
						"title":       title,
						"description": desc,
						"url":         "https://3d.bstccc.cn/#/machine",
						"picurl":      picUrl,
					},
				},
			},
		}
	} else {
		payload = map[string]any{
			"touser":  toUser,
			"msgtype": "textcard",
			"agentid": agentId,
			"textcard": map[string]any{
				"title":       title,
				"description": desc,
				"url":         "https://3d.bstccc.cn/#/machine",
				"btntxt":      "查看详情",
			},
		}
	}
	b, _ := json.Marshal(payload)
	req, _ := http.NewRequest("POST", "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="+token, bytes.NewReader(b))
	req.Header.Set("Content-Type", "application/json")
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	rb, _ := io.ReadAll(resp.Body)
	var sent struct {
		ErrCode int    `json:"errcode"`
		ErrMsg  string `json:"errmsg"`
	}
	_ = json.Unmarshal(rb, &sent)
	if sent.ErrCode != 0 {
		return fmt.Errorf("WeCom 拒绝(%d): %s", sent.ErrCode, sent.ErrMsg)
	}
	return nil
}

// ezvizCaptureJPEG 通过萤石开放平台抓一张快照：返回图片本体与签名 OSS URL
// （URL 可直接作为企业微信 news 消息的配图）。
func (s *Server) ezvizCaptureJPEG() ([]byte, string, error) {
	cfg := s.st.LoadSettings()
	if cfg.Ezviz.AppKey == "" || cfg.Ezviz.DeviceSerial == "" {
		return nil, "", fmt.Errorf("萤石未配置")
	}
	s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
	token, err := s.ez.AccessToken()
	if err != nil {
		return nil, "", fmt.Errorf("萤石 token: %w", err)
	}
	channel := cfg.Ezviz.Channel
	if channel == "" {
		channel = "1"
	}
	form := url.Values{}
	form.Set("accessToken", token)
	form.Set("deviceSerial", cfg.Ezviz.DeviceSerial)
	form.Set("channelNo", channel)
	res, err := http.PostForm("https://open.ys7.com/api/lapp/device/capture", form)
	if err != nil {
		return nil, "", err
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	var parsed struct {
		Code string `json:"code"`
		Msg  string `json:"msg"`
		Data struct {
			PicUrl string `json:"picUrl"`
		} `json:"data"`
	}
	if err := json.Unmarshal(raw, &parsed); err != nil {
		return nil, "", fmt.Errorf("萤石响应解析失败: %w", err)
	}
	if parsed.Code != "200" && parsed.Code != "20006" && parsed.Code != "0" {
		return nil, "", fmt.Errorf("萤石抓拍失败(%s): %s", parsed.Code, parsed.Msg)
	}
	if parsed.Data.PicUrl == "" {
		return nil, "", fmt.Errorf("萤石未返回抓拍地址")
	}
	for attempt := 0; attempt < 2; attempt++ {
		client := &http.Client{Timeout: 20 * time.Second}
		resp, gerr := client.Get(parsed.Data.PicUrl)
		if gerr == nil {
			jpeg, rerr := io.ReadAll(resp.Body)
			resp.Body.Close()
			if rerr == nil && len(jpeg) > 1024 && jpeg[0] == 0xFF && jpeg[1] == 0xD8 {
				return jpeg, parsed.Data.PicUrl, nil
			}
		}
		time.Sleep(time.Second)
	}
	return nil, "", fmt.Errorf("抓拍图片下载失败")
}

// visionCompareMonitor 把两张快照发给视觉模型（DeepSeek OpenAI 兼容格式，
// image_url 传 base64 data URL）对比判断。返回 anomaly/level/desc 与原文。
func (s *Server) visionCompareMonitor(prevJPEG, curJPEG []byte) (anomaly bool, level, desc, raw string, err error) {
	cfg := s.st.LoadSettings()
	if cfg.AI.APIKey == "" {
		return false, "", "", "", fmt.Errorf("未配置 Vision API Key（设置页 AI 视觉识别）")
	}
	endpoint := strings.TrimSpace(cfg.AI.Endpoint)
	if endpoint == "" {
		// 未填 Endpoint 时按 DeepSeek 官方 BASE URL 处理
		endpoint = "https://api.deepseek.com"
	}
	model := strings.TrimSpace(cfg.AI.Model)
	if model == "" {
		model = "deepseek-flash"
	}

	b64Prev := base64.StdEncoding.EncodeToString(prevJPEG)
	b64Cur := base64.StdEncoding.EncodeToString(curJPEG)

	prompt := buildMonitorPrompt(cfg.Ezviz.Rotation)
	payload := map[string]any{
		"model": model,
		"messages": []any{
			map[string]any{"role": "system", "content": prompt},
			map[string]any{
				"role": "user",
				"content": []any{
					map[string]any{"type": "text", "text": "第一张（较早）："},
					map[string]any{"type": "image_url", "image_url": map[string]any{"url": "data:image/jpeg;base64," + b64Prev}},
					map[string]any{"type": "text", "text": "第二张（较晚）："},
					map[string]any{"type": "image_url", "image_url": map[string]any{"url": "data:image/jpeg;base64," + b64Cur}},
					map[string]any{"type": "text", "text": "请对比并输出 JSON 结论。"},
				},
			},
		},
		"temperature": 0.1,
		"stream":      false,
	}
	reqBody, _ := json.Marshal(payload)

	reqURL := strings.TrimRight(endpoint, "/") + "/chat/completions"
	httpReq, err := http.NewRequest(http.MethodPost, reqURL, bytes.NewReader(reqBody))
	if err != nil {
		return false, "", "", "", err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	httpReq.Header.Set("Authorization", "Bearer "+cfg.AI.APIKey)

	client := &http.Client{Timeout: 150 * time.Second}
	resp, err := client.Do(httpReq)
	if err != nil {
		return false, "", "", "", err
	}
	defer resp.Body.Close()
	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return false, "", "", "", err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return false, "", "", "", fmt.Errorf("视觉 API HTTP %d: %s", resp.StatusCode, string(respBytes))
	}

	var openaiResp struct {
		Choices []struct {
			Message struct {
				Content string `json:"content"`
			} `json:"message"`
		} `json:"choices"`
	}
	if err := json.Unmarshal(respBytes, &openaiResp); err != nil || len(openaiResp.Choices) == 0 {
		return false, "", "", "", fmt.Errorf("视觉 API 响应解析失败: %s", string(respBytes[:min(200, len(respBytes))]))
	}
	raw = strings.TrimSpace(openaiResp.Choices[0].Message.Content)
	raw = strings.TrimPrefix(raw, "```json")
	raw = strings.TrimPrefix(raw, "```")
	raw = strings.TrimSuffix(raw, "```")
	raw = strings.TrimSpace(raw)

	var res struct {
		Anomaly bool   `json:"anomaly"`
		Level   string `json:"level"`
		Desc    string `json:"desc"`
	}
	if err := json.Unmarshal([]byte(raw), &res); err != nil {
		// 模型未按 JSON 返回时，把原文当作描述（不误报异常）
		return false, "none", raw, raw, nil
	}
	return res.Anomaly, res.Level, res.Desc, raw, nil
}
