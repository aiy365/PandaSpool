package bambu

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
)

type CloudFilament struct {
	ID             int64    `json:"id"`
	CreateType     string   `json:"createType"`
	FilamentVendor string   `json:"filamentVendor"`
	FilamentType   string   `json:"filamentType"`
	FilamentName   string   `json:"filamentName"`
	FilamentID     string   `json:"filamentId"`
	RFID           string   `json:"RFID"`
	Color          string   `json:"color"`
	ColorType      int      `json:"colorType"`
	Colors         []string `json:"colors"`
	NetWeight      int      `json:"netWeight"`
	TotalNetWeight int      `json:"totalNetWeight"`
	Note           string   `json:"note"`
	IsSupport      bool     `json:"isSupport"`
	TrayIDName     string   `json:"trayIdName"`
	Category       string   `json:"category"`
	InPrinter      bool     `json:"inPrinter"`
	Depleted       bool     `json:"depleted"`
}

type CloudAdapter struct {
	region string
	token  string
}

func NewCloudAdapter(region, token string) *CloudAdapter {
	return &CloudAdapter{
		region: region,
		token:  token,
	}
}

func (a *CloudAdapter) request(method, path string, body any) ([]byte, error) {
	url := apiBase(a.region) + path
	var reqBody io.Reader
	if body != nil {
		b, err := json.Marshal(body)
		if err != nil {
			return nil, err
		}
		reqBody = bytes.NewReader(b)
	}

	req, err := http.NewRequest(method, url, reqBody)
	if err != nil {
		return nil, err
	}

	for k, v := range slicerHeaders() {
		req.Header.Set(k, v)
	}
	req.Header.Set("User-Agent", "BBL-Slicer/1.9.0")
	req.Header.Set("Authorization", "Bearer "+a.token)

	res, err := http.DefaultClient.Do(req)
	if err != nil {
		return nil, err
	}
	defer res.Body.Close()

	raw, err := io.ReadAll(res.Body)
	if err != nil {
		return nil, err
	}

	if res.StatusCode >= 400 {
		return nil, fmt.Errorf("HTTP %d: %s", res.StatusCode, string(raw))
	}

	return raw, nil
}

func (a *CloudAdapter) ListFilaments() ([]CloudFilament, error) {
	raw, err := a.request(http.MethodGet, "/v1/design-user-service/my/filament/v2?limit=500", nil)
	if err != nil {
		return nil, err
	}

	var resp struct {
		Hits []CloudFilament `json:"hits"`
	}
	if err := json.Unmarshal(raw, &resp); err != nil {
		return nil, err
	}

	return resp.Hits, nil
}

func (a *CloudAdapter) CreateFilament(f CloudFilament) (int64, error) {
	if strings.TrimSpace(f.Note) == "" {
		return 0, fmt.Errorf("建档备注不能为空（用于回查云端 ID）")
	}
	_, err := a.request(http.MethodPost, "/v1/design-user-service/my/filament/v2", f)
	if err != nil {
		return 0, err
	}

	// POST 返回空 JSON。按备注精确回查新条目——同规格多卷只差备注里的
	// 短编号，按"ID 最大的"猜会绑错盘。
	filaments, err := a.ListFilaments()
	if err != nil {
		return 0, err
	}
	for _, fil := range filaments {
		if fil.ID > 0 && fil.Note == f.Note {
			return fil.ID, nil
		}
	}
	return 0, fmt.Errorf("云端已建档但未回查到备注 %q 的条目（列表可能延迟，稍后在「云端对账」里补绑）", f.Note)
}

// TruncateRunes 按字符截断，避免切坏中文。
func TruncateRunes(s string, n int) string {
	r := []rune(s)
	if len(r) <= n {
		return s
	}
	return string(r[:n])
}

func (a *CloudAdapter) UpdateWeight(id int64, filamentName string, netWeight int) error {
	body := map[string]any{
		"id":           id,
		"filamentName": filamentName,
		"netWeight":    netWeight,
	}
	_, err := a.request(http.MethodPut, "/v1/design-user-service/my/filament/v2", body)
	return err
}

func (a *CloudAdapter) DeleteFilaments(ids []int64) error {
	if len(ids) == 0 {
		return nil
	}
	body := map[string]any{
		"ids": ids,
	}
	_, err := a.request(http.MethodDelete, "/v1/design-user-service/my/filament/v2/batch", body)
	return err
}
