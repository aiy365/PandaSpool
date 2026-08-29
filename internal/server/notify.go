package server

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strconv"
	"time"
)

// layerInt 把打印机上报的层数转成整数；未知返回 -1。
func layerInt(v any) int {
	switch t := v.(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		n, _ := strconv.Atoi(t)
		return n
	}
	return -1
}

// tickNotifications 每 10 秒巡检一次打印状态并决定是否推送。
//
// 首层提醒是"任务感知"的：只有亲眼见过当前任务处于第 0/1 层，之后到达
// 第 2 层及以上才提醒。这样服务重启时不会把进行中的任务误报成"首层完成"
// （重启后没见过首层，就保持沉默），重印同名文件也会因任务结束被重置而
// 正常提醒。
func (s *Server) tickNotifications() {
	cfg := s.st.LoadSettings()
	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	if wcCorp == "" || wcSec == "" {
		return
	}

	st := s.bambu.Status()
	gcode, _ := st["gcode_state"].(string)
	subtask, _ := st["subtask"].(string)
	layerNum := layerInt(st["layer"])
	var endedAt time.Time
	if endStr, ok := st["print_ended_at"].(string); ok && endStr != "" {
		endedAt, _ = time.Parse(time.RFC3339, endStr)
	}

	active := gcode == "PREPARE" || gcode == "RUNNING"
	ended := gcode == "FINISH" || gcode == "FINISHED" || gcode == "FAILED" || gcode == "IDLE"

	s.mu.Lock()
	if subtask != s.lastJob || ended {
		s.lastJob = subtask
		s.layer1Seen = false
		s.layer1Notified = false
	}
	if active && (layerNum == 0 || layerNum == 1) {
		s.layer1Seen = true
	}
	shouldNotifyLayer1 := active && s.layer1Seen && !s.layer1Notified && layerNum >= 2
	if shouldNotifyLayer1 {
		s.layer1Notified = true
	}

	shouldNotifyFinish := false
	if !endedAt.IsZero() && time.Since(endedAt) > 10*time.Minute && !s.notifiedPrintEnd.Equal(endedAt) {
		s.notifiedPrintEnd = endedAt
		shouldNotifyFinish = true
	}
	s.mu.Unlock()

	if shouldNotifyLayer1 {
		go s.sendWebhookNotification("🚀 打印任务 - 首层已完成！", st)
	}
	if shouldNotifyFinish {
		go s.sendWebhookNotification("✅ 打印任务 - 已完成 10 分钟", st)
	}
}

// sendWebhookNotification 抓一张监控截图（可失败）后发企业微信应用消息；
// 凭证无效时记日志并放弃，不再静默吞掉。
func (s *Server) sendWebhookNotification(title string, st map[string]any) {
	var picUrl string
	cfg := s.st.LoadSettings()
	if cfg.Ezviz.AppKey != "" && cfg.Ezviz.DeviceSerial != "" {
		s.ez.Configure(cfg.Ezviz.AppKey, cfg.Ezviz.AppSecret)
		if token, err := s.ez.AccessToken(); err == nil && token != "" {
			form := url.Values{}
			form.Set("accessToken", token)
			form.Set("deviceSerial", cfg.Ezviz.DeviceSerial)
			channel := cfg.Ezviz.Channel
			if channel == "" {
				channel = "1"
			}
			form.Set("channelNo", channel)
			if res, err := http.PostForm("https://open.ys7.com/api/lapp/device/capture", form); err == nil {
				defer res.Body.Close()
				raw, _ := io.ReadAll(res.Body)
				var parsed struct {
					Data struct {
						PicUrl string `json:"picUrl"`
					} `json:"data"`
				}
				if json.Unmarshal(raw, &parsed) == nil && parsed.Data.PicUrl != "" {
					picUrl = parsed.Data.PicUrl
				}
			}
		}
	}

	token, err := s.weComAccessToken(cfg)
	if err != nil {
		log.Printf("WeCom 推送跳过（%s）: %v", title, err)
		return
	}

	desc := fmt.Sprintf("打印机状态: %v\n当前层数: %v / %v", st["gcode_state"], st["layer"], st["total_layer"])
	if sub, ok := st["subtask"].(string); ok && sub != "" {
		desc = fmt.Sprintf("任务: %s\n%s", sub, desc)
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
						"url":         picUrl,
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
		log.Printf("WeCom 发送失败: %v", err)
		return
	}
	defer resp.Body.Close()
	rb, _ := io.ReadAll(resp.Body)
	var sent struct {
		ErrCode int    `json:"errcode"`
		ErrMsg  string `json:"errmsg"`
	}
	_ = json.Unmarshal(rb, &sent)
	if sent.ErrCode != 0 {
		log.Printf("WeCom 发送被拒(%d): %s", sent.ErrCode, sent.ErrMsg)
		return
	}
	log.Printf("WeCom 已发送: %s", title)
}
