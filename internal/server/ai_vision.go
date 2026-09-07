package server

import (
	"bytes"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"time"

	"pandaspool/internal/store"
)

type ProductSpecsReq struct {
	ProductLine   string `json:"product_line"`
	BambuPresetID string `json:"bambu_preset_id"`
	Notes         string `json:"notes"`
	NozzleRange   string `json:"nozzle_range"`
	NozzleRec     string `json:"nozzle_rec"`
	BedRange      string `json:"bed_range"`
	BedRec        string `json:"bed_rec"`
	DryTemp       string `json:"dry_temp"`
	DryTime       string `json:"dry_time"`
	SpeedMax      string `json:"speed_max"`
	Density       string `json:"density"`
}

func (s *Server) productUpdateSpecs(w http.ResponseWriter, r *http.Request, productID string) {
	var req ProductSpecsReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "无效的 JSON 请求", http.StatusBadRequest)
		return
	}

	p, err := s.st.GetProduct(productID)
	if err != nil {
		http.Error(w, "产品不存在", http.StatusNotFound)
		return
	}

	p.ProductLine = strings.TrimSpace(req.ProductLine)
	p.BambuPresetID = strings.TrimSpace(req.BambuPresetID)
	p.Notes = strings.TrimSpace(req.Notes)
	if _, err := s.st.SaveProduct(p); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// 统一保存或更新核心工况参数（confirmed）
	applySpecClaim := func(key, val, unit string) {
		val = strings.TrimSpace(val)
		if val == "" {
			return
		}
		_, _ = s.st.SaveClaim(store.Claim{
			ProductID: productID,
			Source:    "资料",
			Key:       key,
			Value:     val,
			Unit:      unit,
			Status:    store.ClaimConfirmed,
		})
	}

	applySpecClaim("喷嘴温度范围", req.NozzleRange, "°C")
	applySpecClaim("喷嘴推荐温度", req.NozzleRec, "°C")
	applySpecClaim("热床温度范围", req.BedRange, "°C")
	applySpecClaim("热床推荐温度", req.BedRec, "°C")
	applySpecClaim("烘干温度范围", req.DryTemp, "°C")
	applySpecClaim("烘干时间", req.DryTime, "小时")
	applySpecClaim("打印速度上限", req.SpeedMax, "mm/s")
	applySpecClaim("密度", req.Density, "g/cm³")

	updated, _ := s.st.GetProduct(productID)
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]any{"ok": true, "product": updated, "hint": "工况与基础信息已保存"})
}

type VisionExtracted struct {
	Brand       string   `json:"brand"`
	ProductLine string   `json:"product_line"`
	Material    string   `json:"material"`
	NozzleRange string   `json:"nozzle_range"`
	NozzleRec   string   `json:"nozzle_rec"`
	BedRange    string   `json:"bed_range"`
	BedRec      string   `json:"bed_rec"`
	DryTemp     string   `json:"dry_temp"`
	DryTime     string   `json:"dry_time"`
	SpeedMax    string   `json:"speed_max"`
	Density     string   `json:"density"`
	Colors      []string `json:"colors"`
	Notes       string   `json:"notes"`
}

func (s *Server) productAIVision(w http.ResponseWriter, r *http.Request, productID string) {
	w.Header().Set("Content-Type", "application/json")

	var imgBytes []byte
	var mimeType string
	var filename string

	// 判断是上传图片还是已有 inbox 图片
	if strings.HasPrefix(r.Header.Get("Content-Type"), "multipart/form-data") {
		if err := r.ParseMultipartForm(store.MaxInboxBytes); err != nil {
			http.Error(w, "图片解析失败", http.StatusBadRequest)
			return
		}
		files := r.MultipartForm.File["file"]
		if len(files) == 0 {
			files = r.MultipartForm.File["files"]
		}
		if len(files) == 0 {
			http.Error(w, "未收到上传图片", http.StatusBadRequest)
			return
		}
		fh := files[0]
		f, err := fh.Open()
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		imgBytes, err = io.ReadAll(f)
		f.Close()
		if err != nil {
			http.Error(w, err.Error(), http.StatusBadRequest)
			return
		}
		filename = fh.Filename
		mimeType = store.DetectImageMIME(imgBytes)
		if mimeType == "" {
			mimeType = "image/jpeg"
		}
	} else {
		// JSON 传入 inbox_id
		var body struct {
			InboxID string `json:"inbox_id"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		if body.InboxID == "" {
			http.Error(w, "请提供图片文件或 inbox_id", http.StatusBadRequest)
			return
		}
		items, _ := s.st.ListInbox(productID)
		var target *store.InboxItem
		for _, it := range items {
			if it.ID == body.InboxID {
				target = &it
				break
			}
		}
		if target == nil {
			http.Error(w, "未找到指定的图片凭据", http.StatusNotFound)
			return
		}
		p := store.InboxPath(s.st.DataDir, target.SHA256)
		b, err := os.ReadFile(p)
		if err != nil {
			http.Error(w, "读取凭据文件失败", http.StatusInternalServerError)
			return
		}
		imgBytes = b
		mimeType = target.MIME
		filename = target.Name
	}

	// 先存入 inbox 作为档案凭据
	inboxItem, _ := s.st.SaveInboxFile(productID, "", filename, imgBytes)

	cfg := s.st.LoadSettings()
	if cfg.AI.APIKey == "" {
		// 未配置 Vision Key，给前端友好引导
		json.NewEncoder(w).Encode(map[string]any{
			"ok":         false,
			"error":      "not_configured",
			"hint":       "图片已保存到凭据库。当前尚未配置 Vision API Key，可前往「设置」配置，或直接在聊天窗口发给助手提取。",
			"inbox_item": store.InboxPublic(inboxItem),
		})
		return
	}

	// 调用外部 Vision API 进行结构化抽取
	extracted, err := callVisionAPI(cfg.AI.Endpoint, cfg.AI.APIKey, cfg.AI.Model, imgBytes, mimeType)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{
			"ok":         false,
			"error":      "ai_call_failed",
			"hint":       "AI 视觉识别调用失败: " + err.Error(),
			"inbox_item": store.InboxPublic(inboxItem),
		})
		return
	}

	// 将 AI 识别结果自动写回产品
	p, err := s.st.GetProduct(productID)
	if err == nil {
		modified := false
		if p.ProductLine == "" && extracted.ProductLine != "" {
			p.ProductLine = extracted.ProductLine
			modified = true
		}
		if extracted.Notes != "" {
			if p.Notes == "" {
				p.Notes = extracted.Notes
			} else if !strings.Contains(p.Notes, extracted.Notes) {
				p.Notes = p.Notes + "\n" + extracted.Notes
			}
			modified = true
		}
		if modified {
			_, _ = s.st.SaveProduct(p)
		}
	}

	// 自动写入工况参数（标记为 AI识别 且已确认）
	saveAIClaim := func(key, val, unit string) {
		val = strings.TrimSpace(val)
		if val == "" {
			return
		}
		_, _ = s.st.SaveClaim(store.Claim{
			ProductID: productID,
			Source:    "AI识别",
			Key:       key,
			Value:     val,
			Unit:      unit,
			Raw:       "AI 识别自凭据图",
			Status:    store.ClaimConfirmed,
		})
	}

	saveAIClaim("喷嘴温度范围", extracted.NozzleRange, "°C")
	saveAIClaim("喷嘴推荐温度", extracted.NozzleRec, "°C")
	saveAIClaim("热床温度范围", extracted.BedRange, "°C")
	saveAIClaim("热床推荐温度", extracted.BedRec, "°C")
	saveAIClaim("烘干温度范围", extracted.DryTemp, "°C")
	saveAIClaim("烘干时间", extracted.DryTime, "小时")
	saveAIClaim("打印速度上限", extracted.SpeedMax, "mm/s")
	saveAIClaim("密度", extracted.Density, "g/cm³")

	// 自动建立识别到的颜色
	for _, cname := range extracted.Colors {
		cname = strings.TrimSpace(cname)
		if cname != "" {
			_, _ = s.st.EnsureColor(productID, cname)
		}
	}

	_ = s.st.SetInboxStatus(inboxItem.ID, store.InboxProcessed)

	updated, _ := s.st.GetProduct(productID)
	json.NewEncoder(w).Encode(map[string]any{
		"ok":         true,
		"extracted":  extracted,
		"product":    updated,
		"inbox_item": store.InboxPublic(inboxItem),
		"hint":       "AI 识别成功！已自动提取并写入工艺温度与基础信息。",
	})
}

func (s *Server) productAICreate(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	if err := r.ParseMultipartForm(store.MaxInboxBytes); err != nil {
		http.Error(w, "图片解析失败", http.StatusBadRequest)
		return
	}
	files := r.MultipartForm.File["file"]
	if len(files) == 0 {
		files = r.MultipartForm.File["files"]
	}
	if len(files) == 0 {
		http.Error(w, "未收到上传图片", http.StatusBadRequest)
		return
	}
	fh := files[0]
	f, err := fh.Open()
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	imgBytes, err := io.ReadAll(f)
	f.Close()
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	filename := fh.Filename
	mimeType := store.DetectImageMIME(imgBytes)
	if mimeType == "" {
		mimeType = "image/jpeg"
	}

	cfg := s.st.LoadSettings()
	if cfg.AI.APIKey == "" {
		json.NewEncoder(w).Encode(map[string]any{
			"ok":    false,
			"error": "not_configured",
			"hint":  "未配置 Vision API Key，请先前往「设置」配置视觉模型 Key。",
		})
		return
	}

	extracted, err := callVisionAPI(cfg.AI.Endpoint, cfg.AI.APIKey, cfg.AI.Model, imgBytes, mimeType)
	if err != nil {
		json.NewEncoder(w).Encode(map[string]any{
			"ok":    false,
			"error": "ai_call_failed",
			"hint":  "AI 识图建档失败: " + err.Error(),
		})
		return
	}

	brand := strings.TrimSpace(extracted.Brand)
	if brand == "" {
		brand = "自定品牌"
	}
	material := strings.TrimSpace(extracted.Material)
	if material == "" {
		material = "PLA"
	}
	prodLine := strings.TrimSpace(extracted.ProductLine)

	newProd, err := s.st.SaveProduct(store.Product{
		Brand:       brand,
		ProductLine: prodLine,
		Material:    material,
		Notes:       extracted.Notes,
	})
	if err != nil {
		http.Error(w, "创建产品失败: "+err.Error(), http.StatusInternalServerError)
		return
	}

	inboxItem, _ := s.st.SaveInboxFile(newProd.ID, "", filename, imgBytes)
	if inboxItem.ID != "" {
		_ = s.st.SetInboxStatus(inboxItem.ID, store.InboxProcessed)
	}

	saveAIClaim := func(key, val, unit string) {
		val = strings.TrimSpace(val)
		if val == "" {
			return
		}
		_, _ = s.st.SaveClaim(store.Claim{
			ProductID: newProd.ID,
			Source:    "AI识别",
			Key:       key,
			Value:     val,
			Unit:      unit,
			Raw:       "AI 识别自建档图片",
			Status:    store.ClaimConfirmed,
		})
	}

	saveAIClaim("喷嘴温度范围", extracted.NozzleRange, "°C")
	saveAIClaim("喷嘴推荐温度", extracted.NozzleRec, "°C")
	saveAIClaim("热床温度范围", extracted.BedRange, "°C")
	saveAIClaim("热床推荐温度", extracted.BedRec, "°C")
	saveAIClaim("烘干温度范围", extracted.DryTemp, "°C")
	saveAIClaim("烘干时间", extracted.DryTime, "小时")
	saveAIClaim("打印速度上限", extracted.SpeedMax, "mm/s")
	saveAIClaim("密度", extracted.Density, "g/cm³")

	for _, cname := range extracted.Colors {
		cname = strings.TrimSpace(cname)
		if cname != "" {
			_, _ = s.st.EnsureColor(newProd.ID, cname)
		}
	}

	json.NewEncoder(w).Encode(map[string]any{
		"ok":         true,
		"product_id": newProd.ID,
		"extracted":  extracted,
		"hint":       "AI 识图建档成功！已自动提取并写入工艺温度与基础信息。",
	})
}

func callVisionAPI(endpoint, apiKey, model string, imgBytes []byte, mimeType string) (*VisionExtracted, error) {
	if endpoint == "" {
		endpoint = "https://api.openai.com/v1"
	}
	endpoint = strings.TrimRight(endpoint, "/")
	if model == "" {
		model = "gpt-4o-mini"
	}

	b64Img := base64.StdEncoding.EncodeToString(imgBytes)
	dataURI := fmt.Sprintf("data:%s;base64,%s", mimeType, b64Img)

	systemPrompt := `你是一个专业的 3D 打印材料与切片工艺专家。请从用户上传的 3D 打印耗材包装贴纸、TDS技术规格表或商品参数截图中提取工艺参数。
必须严格输出且仅输出一个合法的 JSON 对象，不要包含 markdown 格式标记（不要写 ` + "```json" + `），格式如下：
{
  "brand": "品牌名",
  "product_line": "细分系列，如 HF、高透、哑光、高速、碳纤等，如无写空字符串",
  "material": "材料大类，如 PLA, PETG, ABS, TPU, ASA, PC, PA",
  "nozzle_range": "喷嘴温度范围，纯数字范围如 230-250",
  "nozzle_rec": "喷嘴推荐温度，纯数字如 240",
  "bed_range": "热床温度范围，纯数字范围如 70-80",
  "bed_rec": "热床推荐温度，纯数字如 75",
  "dry_temp": "烘干温度，纯数字如 65",
  "dry_time": "烘干时间，如 6h 或 6小时",
  "speed_max": "推荐最高打印速度，纯数字如 250",
  "density": "密度，如 1.27",
  "colors": ["颜色名"],
  "notes": "官方打印建议或特殊注意事项"
}`

	var reqBody []byte
	var reqURL string

	if strings.Contains(strings.ToLower(model), "gemini") && !strings.Contains(endpoint, "/v1") {
		reqURL = fmt.Sprintf("https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent?key=%s", model, apiKey)
		geminiPayload := map[string]any{
			"contents": []any{
				map[string]any{
					"parts": []any{
						map[string]any{"text": systemPrompt},
						map[string]any{
							"inline_data": map[string]any{
								"mime_type": mimeType,
								"data":      b64Img,
							},
						},
					},
				},
			},
		}
		reqBody, _ = json.Marshal(geminiPayload)
	} else {
		// OpenAI 兼容模式
		reqURL = endpoint + "/chat/completions"
		openaiPayload := map[string]any{
			"model": model,
			"messages": []any{
				map[string]any{
					"role": "system",
					"content": systemPrompt,
				},
				map[string]any{
					"role": "user",
					"content": []any{
						map[string]any{"type": "text", "text": "请提取这张耗材图片中的参数："},
						map[string]any{
							"type": "image_url",
							"image_url": map[string]any{
								"url": dataURI,
							},
						},
					},
				},
			},
			"temperature": 0.1,
		}
		reqBody, _ = json.Marshal(openaiPayload)
	}

	client := &http.Client{Timeout: 60 * time.Second}
	httpReq, err := http.NewRequest(http.MethodPost, reqURL, bytes.NewReader(reqBody))
	if err != nil {
		return nil, err
	}
	httpReq.Header.Set("Content-Type", "application/json")
	if !strings.Contains(reqURL, "key=") {
		httpReq.Header.Set("Authorization", "Bearer "+apiKey)
	}

	resp, err := client.Do(httpReq)
	if err != nil {
		return nil, err
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("HTTP %d: %s", resp.StatusCode, string(respBytes))
	}

	// 提取回复文本
	var rawText string
	if strings.Contains(reqURL, "generativelanguage.googleapis.com") {
		var geminiResp struct {
			Candidates []struct {
				Content struct {
					Parts []struct {
						Text string `json:"text"`
					} `json:"parts"`
				} `json:"content"`
			} `json:"candidates"`
		}
		if err := json.Unmarshal(respBytes, &geminiResp); err == nil && len(geminiResp.Candidates) > 0 {
			if len(geminiResp.Candidates[0].Content.Parts) > 0 {
				rawText = geminiResp.Candidates[0].Content.Parts[0].Text
			}
		}
	} else {
		var openaiResp struct {
			Choices []struct {
				Message struct {
					Content string `json:"content"`
				} `json:"message"`
			} `json:"choices"`
		}
		if err := json.Unmarshal(respBytes, &openaiResp); err == nil && len(openaiResp.Choices) > 0 {
			rawText = openaiResp.Choices[0].Message.Content
		}
	}

	rawText = strings.TrimSpace(rawText)
	rawText = strings.TrimPrefix(rawText, "```json")
	rawText = strings.TrimPrefix(rawText, "```")
	rawText = strings.TrimSuffix(rawText, "```")
	rawText = strings.TrimSpace(rawText)

	var res VisionExtracted
	if err := json.Unmarshal([]byte(rawText), &res); err != nil {
		return nil, fmt.Errorf("解析模型返回 JSON 失败: %v, raw: %s", err, rawText)
	}
	return &res, nil
}
