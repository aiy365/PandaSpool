package store

import (
	"database/sql"
	"fmt"
	"time"
)

type Spool struct {
	ID                string   `json:"id"`
	ColorID           string   `json:"color_id"`
	ShortCode         string   `json:"short_code"`
	BambuCloudID      int64    `json:"bambu_cloud_id"`
	BambuVendor       string   `json:"bambu_vendor"`
	BambuFilamentName string   `json:"bambu_filament_name"`
	BambuFilamentID   string   `json:"bambu_filament_id"`
	BambuRegion       string   `json:"bambu_region"`
	ColorHex          string   `json:"color_hex"`
	Status            string   `json:"status"` // unopened, opened, depleted
	GrossWeightG      *float64 `json:"gross_weight_g"`
	EmptyWeightG      *float64 `json:"empty_weight_g"`
	NetWeightG        float64  `json:"net_weight_g"`
	SyncEnabled       bool     `json:"sync_enabled"`
	LastSyncedWeightG *float64 `json:"last_synced_weight_g"`
	LastSyncedAt      string   `json:"last_synced_at"`
	CreatedAt         string   `json:"created_at"`
}

func (s *Store) ListSpools() ([]Spool, error) {
	rows, err := s.DB.Query(`SELECT id, color_id, IFNULL(short_code,''), bambu_cloud_id, IFNULL(bambu_vendor,''), IFNULL(bambu_filament_name,''), IFNULL(bambu_filament_id,''), IFNULL(bambu_region,'cn'), IFNULL(color_hex,''), status, gross_weight_g, empty_weight_g, net_weight_g, IFNULL(sync_enabled,1), last_synced_weight_g, IFNULL(last_synced_at,''), created_at FROM spools ORDER BY CAST(SUBSTR(short_code, 4) AS INTEGER) ASC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var out []Spool
	for rows.Next() {
		var sp Spool
		var syncEnabled int
		if err := rows.Scan(&sp.ID, &sp.ColorID, &sp.ShortCode, &sp.BambuCloudID, &sp.BambuVendor, &sp.BambuFilamentName, &sp.BambuFilamentID, &sp.BambuRegion, &sp.ColorHex, &sp.Status, &sp.GrossWeightG, &sp.EmptyWeightG, &sp.NetWeightG, &syncEnabled, &sp.LastSyncedWeightG, &sp.LastSyncedAt, &sp.CreatedAt); err != nil {
			return nil, err
		}
		sp.SyncEnabled = syncEnabled == 1
		out = append(out, sp)
	}
	if out == nil {
		out = []Spool{}
	}
	return out, nil
}

func (s *Store) GetSpool(id string) (Spool, error) {
	var sp Spool
	var syncEnabled int
	err := s.DB.QueryRow(`SELECT id, color_id, IFNULL(short_code,''), bambu_cloud_id, IFNULL(bambu_vendor,''), IFNULL(bambu_filament_name,''), IFNULL(bambu_filament_id,''), IFNULL(bambu_region,'cn'), IFNULL(color_hex,''), status, gross_weight_g, empty_weight_g, net_weight_g, IFNULL(sync_enabled,1), last_synced_weight_g, IFNULL(last_synced_at,''), created_at FROM spools WHERE id=?`, id).Scan(
		&sp.ID, &sp.ColorID, &sp.ShortCode, &sp.BambuCloudID, &sp.BambuVendor, &sp.BambuFilamentName, &sp.BambuFilamentID, &sp.BambuRegion, &sp.ColorHex, &sp.Status, &sp.GrossWeightG, &sp.EmptyWeightG, &sp.NetWeightG, &syncEnabled, &sp.LastSyncedWeightG, &sp.LastSyncedAt, &sp.CreatedAt,
	)
	sp.SyncEnabled = syncEnabled == 1
	return sp, err
}

func (s *Store) SaveSpool(sp Spool) (Spool, error) {
	if sp.ID == "" {
		sp.ID = NewID()
		if sp.CreatedAt == "" {
			sp.CreatedAt = time.Now().UTC().Format(time.RFC3339)
		}
		if sp.Status == "" {
			sp.Status = "opened"
		}
		if sp.ShortCode == "" {
			sp.ShortCode, _ = s.NextShortCode()
		}
		syncEnabled := 0
		if sp.SyncEnabled {
			syncEnabled = 1
		}
		_, err := s.DB.Exec(`INSERT INTO spools (id, color_id, short_code, bambu_cloud_id, bambu_vendor, bambu_filament_name, bambu_filament_id, bambu_region, color_hex, status, gross_weight_g, empty_weight_g, net_weight_g, sync_enabled, last_synced_weight_g, last_synced_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			sp.ID, sp.ColorID, sp.ShortCode, sp.BambuCloudID, sp.BambuVendor, sp.BambuFilamentName, sp.BambuFilamentID, sp.BambuRegion, sp.ColorHex, sp.Status, sp.GrossWeightG, sp.EmptyWeightG, sp.NetWeightG, syncEnabled, sp.LastSyncedWeightG, sp.LastSyncedAt, sp.CreatedAt)
		return sp, err
	}

	syncEnabled := 0
	if sp.SyncEnabled {
		syncEnabled = 1
	}
	_, err := s.DB.Exec(`UPDATE spools SET color_id=?, short_code=?, bambu_cloud_id=?, bambu_vendor=?, bambu_filament_name=?, bambu_filament_id=?, bambu_region=?, color_hex=?, status=?, gross_weight_g=?, empty_weight_g=?, net_weight_g=?, sync_enabled=?, last_synced_weight_g=?, last_synced_at=? WHERE id=?`,
		sp.ColorID, sp.ShortCode, sp.BambuCloudID, sp.BambuVendor, sp.BambuFilamentName, sp.BambuFilamentID, sp.BambuRegion, sp.ColorHex, sp.Status, sp.GrossWeightG, sp.EmptyWeightG, sp.NetWeightG, syncEnabled, sp.LastSyncedWeightG, sp.LastSyncedAt, sp.ID)
	return sp, err
}

func (s *Store) NextShortCode() (string, error) {
	var maxCode sql.NullString
	err := s.DB.QueryRow(`SELECT short_code FROM spools WHERE short_code LIKE 'PP-%' ORDER BY CAST(SUBSTR(short_code, 4) AS INTEGER) DESC LIMIT 1`).Scan(&maxCode)
	if err != nil && err != sql.ErrNoRows {
		return "", err
	}

	var seq int
	if maxCode.Valid && maxCode.String != "" {
		_, _ = fmt.Sscanf(maxCode.String, "PP-%d", &seq)
	}
	seq++
	return fmt.Sprintf("PP-%03d", seq), nil
}

func (s *Store) UpdateSpoolWeight(id string, netWeightG float64) error {
	_, err := s.DB.Exec(`UPDATE spools SET net_weight_g=? WHERE id=?`, netWeightG, id)
	return err
}

func (s *Store) SetSpoolStatus(id string, status string) error {
	_, err := s.DB.Exec(`UPDATE spools SET status=? WHERE id=?`, status, id)
	return err
}

func (s *Store) DeleteSpool(id string) error {
	_, err := s.DB.Exec(`DELETE FROM spools WHERE id=?`, id)
	return err
}
