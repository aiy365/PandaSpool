package store

import (
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	InboxPending   = "pending"
	InboxProcessed = "processed"
	MaxInboxBytes  = 8 << 20
	MaxInboxBatch  = 10
)

type InboxItem struct {
	ID        string `json:"id"`
	ProductID string `json:"product_id"`
	ColorID   string `json:"color_id,omitempty"`
	Name      string `json:"name"`
	SHA256    string `json:"sha256"`
	MIME      string `json:"mime"`
	Size      int64  `json:"size"`
	Status    string `json:"status"`
	Note      string `json:"note"`
	CreatedAt string `json:"created_at"`
}

func (s *Store) migrateInbox() error {
	_, err := s.DB.Exec(`
CREATE TABLE IF NOT EXISTS inbox (
  id TEXT PRIMARY KEY,
  product_id TEXT NOT NULL,
  color_id TEXT,
  name TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  mime TEXT NOT NULL,
  size INTEGER NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  note TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS inbox_product ON inbox(product_id, status);
`)
	return err
}

func InboxDir(dataDir string) string {
	return filepath.Join(dataDir, "files", "inbox")
}

func InboxPath(dataDir, sha string) string {
	return filepath.Join(InboxDir(dataDir), sha)
}

func DetectImageMIME(b []byte) string {
	if len(b) >= 3 && b[0] == 0xff && b[1] == 0xd8 && b[2] == 0xff {
		return "image/jpeg"
	}
	if len(b) >= 8 && string(b[:8]) == "\x89PNG\r\n\x1a\n" {
		return "image/png"
	}
	if len(b) >= 12 && string(b[:4]) == "RIFF" && string(b[8:12]) == "WEBP" {
		return "image/webp"
	}
	if len(b) >= 6 && (string(b[:6]) == "GIF87a" || string(b[:6]) == "GIF89a") {
		return "image/gif"
	}
	return ""
}

func (s *Store) SaveInboxFile(productID, colorID, origName string, body []byte) (InboxItem, error) {
	var empty InboxItem
	if productID == "" {
		return empty, fmt.Errorf("未指定产品")
	}
	if len(body) == 0 {
		return empty, fmt.Errorf("空文件")
	}
	if len(body) > MaxInboxBytes {
		return empty, fmt.Errorf("单张不超过 8MB")
	}
	mime := DetectImageMIME(body)
	if mime == "" {
		return empty, fmt.Errorf("只收 JPG / PNG / WebP / GIF")
	}
	sum := sha256.Sum256(body)
	sha := hex.EncodeToString(sum[:])
	var existing InboxItem
	err := s.DB.QueryRow(`SELECT id,product_id,IFNULL(color_id,''),name,sha256,mime,size,status,note,created_at FROM inbox WHERE product_id=? AND sha256=?`, productID, sha).
		Scan(&existing.ID, &existing.ProductID, &existing.ColorID, &existing.Name, &existing.SHA256, &existing.MIME, &existing.Size, &existing.Status, &existing.Note, &existing.CreatedAt)
	if err == nil {
		return existing, nil
	}
	if err := os.MkdirAll(InboxDir(s.DataDir), 0o700); err != nil {
		return empty, err
	}
	path := InboxPath(s.DataDir, sha)
	if _, err := os.Stat(path); err != nil {
		if err := os.WriteFile(path, body, 0o600); err != nil {
			return empty, err
		}
	}
	name := filepath.Base(origName)
	if name == "" || name == "." {
		name = sha[:12]
	}
	it := InboxItem{
		ID: NewID(), ProductID: productID, ColorID: colorID, Name: name,
		SHA256: sha, MIME: mime, Size: int64(len(body)), Status: InboxPending,
		CreatedAt: time.Now().UTC().Format(time.RFC3339),
	}
	var color any
	if colorID == "" {
		color = nil
	} else {
		color = colorID
	}
	_, err = s.DB.Exec(`INSERT INTO inbox(id,product_id,color_id,name,sha256,mime,size,status,note,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)`,
		it.ID, it.ProductID, color, it.Name, it.SHA256, it.MIME, it.Size, it.Status, it.Note, it.CreatedAt)
	return it, err
}

func scanInbox(rows interface {
	Next() bool
	Scan(dest ...any) error
	Err() error
}) ([]InboxItem, error) {
	var out []InboxItem
	for rows.Next() {
		var it InboxItem
		if err := rows.Scan(&it.ID, &it.ProductID, &it.ColorID, &it.Name, &it.SHA256, &it.MIME, &it.Size, &it.Status, &it.Note, &it.CreatedAt); err != nil {
			return nil, err
		}
		out = append(out, it)
	}
	if out == nil {
		out = []InboxItem{}
	}
	return out, rows.Err()
}

func (s *Store) ListInbox(productID string) ([]InboxItem, error) {
	rows, err := s.DB.Query(`SELECT id,product_id,IFNULL(color_id,''),name,sha256,mime,size,status,note,created_at FROM inbox WHERE product_id=? ORDER BY created_at DESC`, productID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanInbox(rows)
}

func (s *Store) ListPendingInbox() ([]InboxItem, error) {
	rows, err := s.DB.Query(`SELECT id,product_id,IFNULL(color_id,''),name,sha256,mime,size,status,note,created_at FROM inbox WHERE status=? ORDER BY created_at ASC`, InboxPending)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	return scanInbox(rows)
}

func (s *Store) GetInbox(id string) (InboxItem, error) {
	var it InboxItem
	err := s.DB.QueryRow(`SELECT id,product_id,IFNULL(color_id,''),name,sha256,mime,size,status,note,created_at FROM inbox WHERE id=?`, id).
		Scan(&it.ID, &it.ProductID, &it.ColorID, &it.Name, &it.SHA256, &it.MIME, &it.Size, &it.Status, &it.Note, &it.CreatedAt)
	return it, err
}

func (s *Store) SetInboxStatus(id, status string) error {
	if status != InboxPending && status != InboxProcessed {
		return fmt.Errorf("未知状态")
	}
	res, err := s.DB.Exec(`UPDATE inbox SET status=? WHERE id=?`, status, id)
	if err != nil {
		return err
	}
	n, _ := res.RowsAffected()
	if n == 0 {
		return fmt.Errorf("找不到这张图")
	}
	return nil
}

func (s *Store) DeleteInbox(id string) error {
	_, err := s.DB.Exec(`DELETE FROM inbox WHERE id=?`, id)
	return err
}

func (s *Store) InboxPendingCount(productID string) int {
	var n int
	if productID == "" {
		_ = s.DB.QueryRow(`SELECT COUNT(*) FROM inbox WHERE status=?`, InboxPending).Scan(&n)
	} else {
		_ = s.DB.QueryRow(`SELECT COUNT(*) FROM inbox WHERE product_id=? AND status=?`, productID, InboxPending).Scan(&n)
	}
	return n
}

func InboxPublic(it InboxItem) map[string]any {
	return map[string]any{
		"id": it.ID, "product_id": it.ProductID, "color_id": it.ColorID,
		"name": it.Name, "mime": it.MIME, "size": it.Size, "status": it.Status,
		"note": it.Note, "created_at": it.CreatedAt,
		"url": "/api/inbox/" + it.ID + "/file",
	}
}

func SanitizeNote(s string) string {
	s = strings.TrimSpace(s)
	if len(s) > 500 {
		return s[:500]
	}
	return s
}
