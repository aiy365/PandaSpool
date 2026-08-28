package server

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"
)

func (s *Server) tickNotifications() {
	cfg := s.st.LoadSettings()
	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	if wcCorp == "" || wcSec == "" {
		return
	}

	st := s.bambu.Status()
	gcode, _ := st["gcode_state"].(string)
	layerVal := fmt.Sprint(st["layer"])
	if layerVal == "<nil>" {
		layerVal = "0"
	}
	var endedAt time.Time
	if endStr, ok := st["print_ended_at"].(string); ok && endStr != "" {
		endedAt, _ = time.Parse(time.RFC3339, endStr)
	}

	s.mu.Lock()
	if (gcode == "PREPARE" || gcode == "RUNNING") && layerVal == "0" {
		s.notifiedLayer1 = false
	}

	shouldNotifyLayer1 := false
	if !s.notifiedLayer1 && endedAt.IsZero() && (gcode == "PREPARE" || gcode == "RUNNING") && layerVal != "0" && layerVal != "1" {
		// If layer is 2 or higher, it means layer 1 has finished
		s.notifiedLayer1 = true
		shouldNotifyLayer1 = true
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

func (s *Server) sendWebhookNotification(title string, st map[string]any) {
	fmt.Println("sendWebhookNotification CALLED with title:", title)
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

	wcCorp := cfg.Automations.WeComCorpID
	wcSec := cfg.Automations.WeComSecret
	wcAgent := cfg.Automations.WeComAgentID
	wcTo := cfg.Automations.WeComToUser

	fmt.Println("WeCom Config:", wcCorp, len(wcSec))
	if wcCorp != "" && wcSec != "" {
		res, err := http.Get(fmt.Sprintf("https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid=%s&corpsecret=%s", wcCorp, wcSec))
		if err == nil {
			defer res.Body.Close()
			raw, _ := io.ReadAll(res.Body)
			var parsed struct {
				AccessToken string `json:"access_token"`
			}
			if json.Unmarshal(raw, &parsed) == nil && parsed.AccessToken != "" {
				desc := fmt.Sprintf("打印机状态: %v\n当前层数: %v / %v", st["gcode_state"], st["layer"], st["total_layer"])
				agentId := 1
				fmt.Sscanf(wcAgent, "%d", &agentId)

				toUser := "@all"
				if wcTo != "" {
					toUser = wcTo
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
				req, _ := http.NewRequest("POST", "https://qyapi.weixin.qq.com/cgi-bin/message/send?access_token="+parsed.AccessToken, bytes.NewReader(b))
				req.Header.Set("Content-Type", "application/json")
				resp, err := http.DefaultClient.Do(req)
				if err != nil {
					fmt.Println("WeCom Send Error:", err)
				} else {
					defer resp.Body.Close()
					rb, _ := io.ReadAll(resp.Body)
					fmt.Println("WeCom Send Response:", string(rb))
				}
			}
		}
	}
}
