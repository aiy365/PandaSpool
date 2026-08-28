package server

import (
	"encoding/json"
	"fmt"
	"net/http"
	"printpilot-hub/internal/bambu"
	"printpilot-hub/internal/store"
	"strings"
)

func (s *Server) spoolsHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodGet {
		s.spoolsList(w, r)
		return
	}
	if r.Method == http.MethodPost {
		s.spoolIntake(w, r)
		return
	}
	http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
}

func (s *Server) spoolItemHandler(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/spools/")
	parts := strings.Split(path, "/")
	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	id := parts[0]

	if len(parts) == 2 {
		if parts[1] == "weight" && r.Method == http.MethodPut {
			s.spoolUpdateWeight(w, r, id)
			return
		}
		if parts[1] == "status" && r.Method == http.MethodPut {
			s.spoolUpdateStatus(w, r, id)
			return
		}
	}

	if len(parts) == 1 && r.Method == http.MethodDelete {
		s.spoolDelete(w, r, id)
		return
	}

	http.Error(w, "not found", http.StatusNotFound)
}

func (s *Server) spoolsList(w http.ResponseWriter, r *http.Request) {
	spools, err := s.st.ListSpools()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(spools)
}

type intakeReq struct {
	ColorID  string `json:"color_id"`
	Quantity int    `json:"quantity"`
}

func getBambuFilamentID(material string) string {
	m := strings.ToUpper(strings.TrimSpace(material))
	if strings.Contains(m, "PLA") {
		return "GFL99"
	}
	if strings.Contains(m, "PETG") {
		return "GFG99"
	}
	if strings.Contains(m, "ABS") {
		return "GFB99"
	}
	if strings.Contains(m, "TPU") {
		return "GFU99"
	}
	return "GFL99"
}

func (s *Server) spoolIntake(w http.ResponseWriter, r *http.Request) {
	var req intakeReq
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	var targetColor *store.Color
	var targetProduct *store.Product
	prods, err := s.st.ListProducts()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	for _, p := range prods {
		for _, c := range p.Colors {
			if c.ID == req.ColorID {
				tc := c
				tp := p
				targetColor = &tc
				targetProduct = &tp
				break
			}
		}
		if targetColor != nil {
			break
		}
	}

	if targetColor == nil || targetProduct == nil {
		http.Error(w, "color not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken == "" {
		http.Error(w, "bambu token not configured", http.StatusBadRequest)
		return
	}

	adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
	filamentID := getBambuFilamentID(targetProduct.Material)

	for i := 0; i < req.Quantity; i++ {
		shortCode, _ := s.st.NextShortCode()
		
		filamentName := fmt.Sprintf("%s %s %s", targetProduct.Brand, targetProduct.Material, targetColor.Name)
		if len(filamentName) > 40 {
			filamentName = filamentName[:40]
		}
		
		f := bambu.CloudFilament{
			FilamentID:   filamentID,
			FilamentName: filamentName,
			Color:        "FF0000FF", // fallback color
			NetWeight:    1000,
		}

		bambuCloudID, err := adapter.CreateFilament(f)
		if err != nil {
			if i > 0 {
				break // partial success, just return what we have
			}
			http.Error(w, fmt.Sprintf("failed to create cloud filament: %v", err), http.StatusInternalServerError)
			return
		}

		sp := store.Spool{
			ColorID:           req.ColorID,
			ShortCode:         shortCode,
			BambuCloudID:      bambuCloudID,
			BambuFilamentID:   filamentID,
			BambuFilamentName: filamentName,
			BambuRegion:       cfg.Bambu.Region,
			NetWeightG:        1000,
			Status:            "unopened",
		}

		_, err = s.st.SaveSpool(sp)
		if err != nil {
			if i > 0 {
				break
			}
			http.Error(w, fmt.Sprintf("failed to save local spool: %v", err), http.StatusInternalServerError)
			return
		}
	}

	s.spoolsList(w, r)
}

func (s *Server) spoolUpdateWeight(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		NetWeightG float64 `json:"net_weight_g"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
		adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
		err = adapter.UpdateWeight(spool.BambuCloudID, spool.BambuFilamentName, int(req.NetWeightG))
		if err != nil {
			// continue and save locally
		}
	}

	err = s.st.UpdateSpoolWeight(id, req.NetWeightG)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) spoolUpdateStatus(w http.ResponseWriter, r *http.Request, id string) {
	var req struct {
		Status string `json:"status"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	if req.Status == "depleted" {
		cfg := s.st.LoadSettings()
		if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
			adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
			adapter.DeleteFilaments([]int64{spool.BambuCloudID})
		}
	}

	err = s.st.SetSpoolStatus(id, req.Status)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}

func (s *Server) spoolDelete(w http.ResponseWriter, r *http.Request, id string) {
	spool, err := s.st.GetSpool(id)
	if err != nil {
		http.Error(w, "spool not found", http.StatusNotFound)
		return
	}

	cfg := s.st.LoadSettings()
	if cfg.Bambu.AccessToken != "" && spool.BambuCloudID > 0 {
		adapter := bambu.NewCloudAdapter(cfg.Bambu.Region, cfg.Bambu.AccessToken)
		adapter.DeleteFilaments([]int64{spool.BambuCloudID})
	}

	err = s.st.DeleteSpool(id)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.Write([]byte(`{"status":"ok"}`))
}
