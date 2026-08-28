package store

import (
	"fmt"
	"math"
	"time"
)

type StockIn struct {
	ID        string  `json:"id"`
	ColorID   string  `json:"color_id"`
	Qty       float64 `json:"qty"`
	UnitPrice float64 `json:"unit_price"`
	Note      string  `json:"note"`
	CreatedAt string  `json:"created_at"`
	Apply     *bool   `json:"apply,omitempty"`
}

func (s *Store) migrateStockIns() error {
	_, err := s.DB.Exec(`
CREATE TABLE IF NOT EXISTS stock_ins (
  id TEXT PRIMARY KEY,
  color_id TEXT NOT NULL,
  qty REAL NOT NULL,
  unit_price REAL NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS stock_ins_color ON stock_ins(color_id, created_at);
`)
	return err
}

func (s *Store) SaveStockIn(in StockIn) (StockIn, error) {
	if in.ColorID == "" {
		return in, fmt.Errorf("颜色不能空")
	}
	if in.Qty <= 0 {
		return in, fmt.Errorf("入库数量必须大于 0")
	}
	if in.UnitPrice < 0 {
		return in, fmt.Errorf("单价不能为负")
	}
	var c Color
	err := s.DB.QueryRow(`SELECT id,product_id,name,color_family,unopened,opened,notes FROM colors WHERE id=?`, in.ColorID).
		Scan(&c.ID, &c.ProductID, &c.Name, &c.ColorFamily, &c.Unopened, &c.Opened, &c.Notes)
	if err != nil {
		return in, fmt.Errorf("颜色不存在")
	}
	apply := in.Apply == nil || *in.Apply
	if in.ID == "" {
		in.ID = NewID()
	}
	if in.CreatedAt == "" {
		in.CreatedAt = time.Now().UTC().Format(time.RFC3339)
	}
	tx, err := s.DB.Begin()
	if err != nil {
		return in, err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`INSERT INTO stock_ins(id,color_id,qty,unit_price,note,created_at) VALUES(?,?,?,?,?,?)`,
		in.ID, in.ColorID, in.Qty, in.UnitPrice, in.Note, in.CreatedAt); err != nil {
		return in, err
	}
	if apply {
		unopened, opened := applyInboundQty(c.Unopened, c.Opened, in.Qty)
		if _, err := tx.Exec(`UPDATE colors SET unopened=?, opened=? WHERE id=?`, unopened, opened, c.ID); err != nil {
			return in, err
		}
	}
	if err := tx.Commit(); err != nil {
		return in, err
	}
	return in, nil
}

func applyInboundQty(unopened, opened int, qty float64) (int, int) {
	whole := int(math.Floor(qty + 1e-9))
	unopened += whole
	if math.Abs(qty-float64(whole)) > 1e-9 {
		opened = 1
	}
	return unopened, opened
}

func (s *Store) ListStockIns(colorID string) ([]StockIn, error) {
	rows, err := s.DB.Query(`SELECT id,color_id,qty,unit_price,note,created_at FROM stock_ins WHERE color_id=? ORDER BY created_at DESC`, colorID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []StockIn
	for rows.Next() {
		var in StockIn
		if err := rows.Scan(&in.ID, &in.ColorID, &in.Qty, &in.UnitPrice, &in.Note, &in.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, in)
	}
	if out == nil {
		out = []StockIn{}
	}
	return out, rows.Err()
}

func (s *Store) ListStockInsByProduct(productID string) ([]StockIn, error) {
	rows, err := s.DB.Query(`
SELECT s.id,s.color_id,s.qty,s.unit_price,s.note,s.created_at
FROM stock_ins s JOIN colors c ON c.id=s.color_id
WHERE c.product_id=?
ORDER BY s.created_at DESC
LIMIT 40`, productID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []StockIn
	for rows.Next() {
		var in StockIn
		if err := rows.Scan(&in.ID, &in.ColorID, &in.Qty, &in.UnitPrice, &in.Note, &in.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, in)
	}
	if out == nil {
		out = []StockIn{}
	}
	return out, rows.Err()
}

func (s *Store) fillColorCost(c *Color) {
	var qty, cost float64
	_ = s.DB.QueryRow(`SELECT IFNULL(SUM(qty),0), IFNULL(SUM(qty*unit_price),0) FROM stock_ins WHERE color_id=? AND unit_price>0`, c.ID).
		Scan(&qty, &cost)
	c.BuyQty = qty
	c.BuyCost = cost
	if qty > 0 {
		c.AvgPrice = cost / qty
	}
}
