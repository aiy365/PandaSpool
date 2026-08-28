package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

type Desk struct {
	OK               bool    `json:"ok"`
	Connected        bool    `json:"connected"`
	Printing         bool    `json:"printing"`
	Progress         float64 `json:"progress"`
	RemainingMin     float64 `json:"remaining_min"`
	ETA              string  `json:"eta"`
	GcodeState       string  `json:"gcode_state"`
	Stage            string  `json:"stage"`
	NozzleTemp       any     `json:"nozzle_temp"`
	NozzleTarget     any     `json:"nozzle_target"`
	BedTemp          any     `json:"bed_temp"`
	BedTarget        any     `json:"bed_target"`
	Layer            any     `json:"layer"`
	TotalLayer       any     `json:"total_layer"`
	Job              any     `json:"job"`
	PrintBoostActive any     `json:"print_boost_active"`
	PrintEndedAt     any     `json:"print_ended_at"`
	UpdatedAt        any     `json:"updated_at"`
	PM1              any     `json:"pm1"`
	PM25             any     `json:"pm25"`
	PM10             any     `json:"pm10"`
	TempC            any     `json:"t_c"`
	RH               any     `json:"rh"`
	Presence         any     `json:"presence"`
	DistanceCM       any     `json:"distance_cm"`
	AirZone          any     `json:"air_zone"`
	AirTS            any     `json:"air_ts"`
	Error            any     `json:"error"`
	FetchErr         string  `json:"-"`
}

func (d Desk) idle() bool {
	return d.FetchErr == "" && d.OK && !d.Printing
}

func fetchDesk(url, token string) Desk {
	if url == "" || token == "" {
		return Desk{FetchErr: "未配置网址或令牌"}
	}
	req, err := http.NewRequest(http.MethodGet, url+"/api/desk", nil)
	if err != nil {
		return Desk{FetchErr: err.Error()}
	}
	req.Header.Set("Authorization", "Bearer "+token)
	client := &http.Client{Timeout: 8 * time.Second}
	res, err := client.Do(req)
	if err != nil {
		return Desk{FetchErr: err.Error()}
	}
	defer res.Body.Close()
	raw, _ := io.ReadAll(res.Body)
	if res.StatusCode != 200 {
		return Desk{FetchErr: fmt.Sprintf("HTTP %d %s", res.StatusCode, truncate(string(raw), 80))}
	}
	var d Desk
	if err := json.Unmarshal(raw, &d); err != nil {
		return Desk{FetchErr: "返回不是 JSON"}
	}
	if d.Printing && d.ETA == "" && d.RemainingMin > 0 {
		d.ETA = time.Now().Add(time.Duration(d.RemainingMin) * time.Minute).Format("15:04")
	}
	return d
}

func fmtAny(v any) string {
	if v == nil {
		return "—"
	}
	switch t := v.(type) {
	case string:
		if t == "" {
			return "—"
		}
		return t
	case bool:
		if t {
			return "是"
		}
		return "否"
	case float64:
		if t == float64(int(t)) {
			return fmt.Sprintf("%d", int(t))
		}
		return fmt.Sprintf("%.1f", t)
	default:
		return fmt.Sprint(t)
	}
}

func fmtUnix(v any) string {
	var n int64
	switch t := v.(type) {
	case float64:
		n = int64(t)
	case int64:
		n = t
	case int:
		n = int64(t)
	case json.Number:
		n, _ = t.Int64()
	default:
		return fmtAny(v)
	}
	if n <= 0 {
		return "—"
	}
	if n > 1e12 {
		n = n / 1000
	}
	return time.Unix(n, 0).Local().Format("01-02 15:04")
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n]
}
