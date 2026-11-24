package server

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"
)

// tickNotifications 每 10 秒巡检一次。现在只保留一个自动提醒：
// 打印结束 10 分钟后的"已完成"通知（每条任务只发一次）。
// 首层提醒与图片抓拍都已下线。
func (s *Server) tickNotifications() {
	cfg := s.st.LoadSettings()
	if cfg.Automations.WeComCorpID == "" || cfg.Automations.WeComSecret == "" {
		return
	}

	st := s.bambu.Status()
	var endedAt time.Time
	if endStr, ok := st["print_ended_at"].(string); ok && endStr != "" {
		endedAt, _ = time.Parse(time.RFC3339, endStr)
	}

	if endedAt.IsZero() || time.Since(endedAt) <= 10*time.Minute || s.notifiedPrintEnd.Equal(endedAt) {
		return
	}
	s.notifiedPrintEnd = endedAt
	go s.sendWebhookNotification("✅ 打印任务 - 已完成 10 分钟", st)
}

// sendWebhookNotification 发企业微信应用消息（textcard，无配图）。
func (s *Server) sendWebhookNotification(title string, st map[string]any) {
	cfg := s.st.LoadSettings()
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

	payload := map[string]any{
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
