package bambu

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
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
	_, err := a.request(http.MethodPost, "/v1/design-user-service/my/filament/v2", f)
	if err != nil {
		return 0, err
	}

	// POST returns empty JSON. Need to list and find the newly created one.
	// Since we don't know the exact ID, we might need to find by some unique attributes or just pick the latest.
	// Wait, the prompt says: "POST 创建后需要再调用 ListFilaments 来找到新增的 ID（POST 返回空 JSON `{}`）"
	filaments, err := a.ListFilaments()
	if err != nil {
		return 0, err
	}
	
	// Try to match the newly created filament
	// We'll return the one with the highest ID assuming it's the newest, or try to match by FilamentName/Color
	var maxID int64
	for _, fil := range filaments {
		if fil.ID > maxID {
			maxID = fil.ID
		}
	}
	
	if maxID == 0 {
		return 0, fmt.Errorf("could not find newly created filament ID")
	}

	return maxID, nil
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
