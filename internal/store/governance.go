package store

import (
	"fmt"
	"strings"
)

func (s *Store) migrateClaimsGovernance() error {
	if err := s.ensureColumn("claims", "status", "TEXT NOT NULL DEFAULT 'confirmed'"); err != nil {
		return err
	}
	if err := s.ensureColumn("claims", "created_at", "TEXT NOT NULL DEFAULT ''"); err != nil {
		return err
	}
	_, _ = s.DB.Exec(`UPDATE claims SET status='confirmed' WHERE status='' OR status IS NULL`)
	_, _ = s.DB.Exec(`UPDATE claims SET source='资料' WHERE source IN ('厂家','商家','manufacturer','厂家TDS','merchant','seller') OR source='' OR source IS NULL`)
	_ = s.migrateTempClaimKeys()
	_, _ = s.DB.Exec(`
DELETE FROM claims WHERE rowid NOT IN (
  SELECT MIN(rowid) FROM claims
  GROUP BY product_id, IFNULL(color_id,''), source, claim_key, claim_value, unit, IFNULL(status,'')
)`)
	return nil
}

func (s *Store) ensureColumn(table, col, decl string) error {
	rows, err := s.DB.Query(`PRAGMA table_info(` + table + `)`)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		var cid int
		var name, ctype string
		var notnull, pk int
		var dflt any
		if err := rows.Scan(&cid, &name, &ctype, &notnull, &dflt, &pk); err != nil {
			return err
		}
		if name == col {
			return nil
		}
	}
	_, err = s.DB.Exec(`ALTER TABLE ` + table + ` ADD COLUMN ` + col + ` ` + decl)
	return err
}

func NormalizeSource(s string) string {
	s = strings.TrimSpace(s)
	switch s {
	case "Studio":
		return "Studio"
	case "实测":
		return "实测"
	}
	switch strings.ToLower(s) {
	case "studio", "bambu":
		return "Studio"
	case "拓竹":
		return "Studio"
	case "measured", "calibration":
		return "实测"
	case "厂家", "商家", "资料", "manufacturer", "厂家tds", "merchant", "seller", "":
		return "资料"
	default:
		return "资料"
	}
}

func (s *Store) reclassifyUnsetFamilies() error {
	rows, err := s.DB.Query(`SELECT id, name, color_family FROM colors WHERE color_family='' OR color_family='未分类'`)
	if err != nil {
		return err
	}
	defer rows.Close()
	type row struct{ id, name, fam string }
	var list []row
	for rows.Next() {
		var r row
		if err := rows.Scan(&r.id, &r.name, &r.fam); err != nil {
			return err
		}
		list = append(list, r)
	}
	for _, r := range list {
		fam := ClassifyColorFamily(r.name)
		if fam == "" || fam == "未分类" || fam == r.fam {
			continue
		}
		if _, err := s.DB.Exec(`UPDATE colors SET color_family=? WHERE id=?`, fam, r.id); err != nil {
			return err
		}
	}
	return nil
}

func ClassifyColorFamily(color string) string {
	value := strings.ToLower(strings.TrimSpace(color))
	if value == "" {
		return "未分类"
	}
	rules := []struct {
		aliases []string
		family  string
	}{
		{[]string{"蓝", "blue"}, "蓝色系"},
		{[]string{"绿", "牛油果", "橄榄", "green", "olive"}, "绿色系"},
		{[]string{"紫", "香芋", "purple", "violet"}, "紫色系"},
		{[]string{"红", "粉", "桃", "rose", "pink", "red"}, "红粉色系"},
		{[]string{"黄", "橙", "柠檬", "yellow", "orange"}, "黄橙色系"},
		{[]string{"棕", "拿铁", "橡木", "咖啡", "肤", "米色", "褐", "杏", "花生", "brown", "beige"}, "棕米色系"},
		{[]string{"金", "银", "铜", "metal", "gold", "silver"}, "金属色系"},
		{[]string{"黑", "灰", "black", "gray", "grey"}, "黑灰色系"},
		{[]string{"白", "white"}, "白色系"},
		{[]string{"彩", "渐变", "虹", "多色", "rainbow", "multicolor"}, "多色/效果色系"},
		{[]string{"透明", "自然", "clear", "transparent", "natural"}, "透明/自然色系"},
	}
	for _, r := range rules {
		for _, a := range r.aliases {
			if strings.Contains(value, strings.ToLower(a)) || strings.Contains(color, a) {
				return r.family
			}
		}
	}
	return "未分类"
}

type Conflict struct {
	Key    string  `json:"key"`
	Values []Claim `json:"values"`
}

func LooksLikeRange(v string) bool {
	return strings.Contains(v, "-") || strings.Contains(v, "~") || strings.Contains(v, "–") || strings.Contains(v, "—")
}

func ClassifyTempKey(key, value, source string) string {
	switch key {
	case "喷嘴温度", "打印温度", "预设打印温度":
		if LooksLikeRange(value) {
			return "喷嘴温度范围"
		}
		if source == "实测" {
			return "喷嘴实测温度"
		}
		return "喷嘴推荐温度"
	case "热床温度", "底板温度", "平台温度":
		if LooksLikeRange(value) {
			return "热床温度范围"
		}
		if source == "实测" {
			return "热床实测温度"
		}
		return "热床推荐温度"
	default:
		return key
	}
}

func (s *Store) migrateTempClaimKeys() error {
	rows, err := s.DB.Query(`SELECT id, claim_key, claim_value, source FROM claims WHERE claim_key IN ('喷嘴温度','打印温度','预设打印温度','热床温度','底板温度','平台温度')`)
	if err != nil {
		return err
	}
	defer rows.Close()
	type row struct{ id, key, value, source string }
	var list []row
	for rows.Next() {
		var r row
		if err := rows.Scan(&r.id, &r.key, &r.value, &r.source); err != nil {
			return err
		}
		list = append(list, r)
	}
	for _, r := range list {
		nk := ClassifyTempKey(r.key, r.value, r.source)
		if nk == r.key {
			continue
		}
		if _, err := s.DB.Exec(`UPDATE claims SET claim_key=? WHERE id=?`, nk, r.id); err != nil {
			return err
		}
	}
	return nil
}

func ConflictsOf(claims []Claim) []Conflict {
	byKey := map[string][]Claim{}
	for _, c := range claims {
		if c.Status != "" && c.Status != ClaimConfirmed {
			continue
		}
		scope := c.Key + "\x00" + c.ColorID
		sig := c.Value + "\x00" + c.Unit
		seen := false
		for _, old := range byKey[scope] {
			if old.Value+"\x00"+old.Unit == sig && old.Source == c.Source {
				seen = true
				break
			}
		}
		if !seen {
			byKey[scope] = append(byKey[scope], c)
		}
	}
	var out []Conflict
	for _, vs := range byKey {
		uniq := map[string]struct{}{}
		for _, v := range vs {
			uniq[v.Value+"\x00"+v.Unit] = struct{}{}
		}
		if len(uniq) > 1 {
			out = append(out, Conflict{Key: vs[0].Key, Values: vs})
		}
	}
	return out
}

func (s *Store) ProductConflicts(productID string) ([]Conflict, error) {
	claims, err := s.ListClaims(productID)
	if err != nil {
		return nil, err
	}
	return ConflictsOf(claims), nil
}

func (s *Store) GovernanceCounts() (drafts, conflicts int) {
	_ = s.DB.QueryRow(`SELECT COUNT(*) FROM claims WHERE status=?`, ClaimDraft).Scan(&drafts)
	list, err := s.ListProducts()
	if err != nil {
		return drafts, 0
	}
	for _, p := range list {
		cs, _ := s.ProductConflicts(p.ID)
		conflicts += len(cs)
	}
	return drafts, conflicts
}

func (s *Store) AIPack() (map[string]any, error) {
	list, err := s.ListProducts()
	if err != nil {
		return nil, err
	}
	drafts, conflicts := s.GovernanceCounts()
	var products []map[string]any
	for _, p := range list {
		all, _ := s.ListClaims(p.ID)
		var confirmed, pending []map[string]any
		for _, c := range all {
			row := map[string]any{
				"id": c.ID, "key": c.Key, "value": c.Value, "unit": c.Unit,
				"source": c.Source, "color_id": c.ColorID, "raw": c.Raw, "status": c.Status,
			}
			switch c.Status {
			case ClaimRejected:
				continue
			case ClaimDraft:
				pending = append(pending, row)
			default:
				confirmed = append(confirmed, row)
			}
		}
		if confirmed == nil {
			confirmed = []map[string]any{}
		}
		if pending == nil {
			pending = []map[string]any{}
		}
		colors := []map[string]any{}
		for _, c := range p.Colors {
			colors = append(colors, map[string]any{
				"id": c.ID, "name": c.Name, "family": c.ColorFamily,
				"unopened": c.Unopened, "opened": c.Opened == 1,
			})
		}
		conf := ConflictsOf(all)
		products = append(products, map[string]any{
			"id": p.ID, "brand": p.Brand, "product_line": p.ProductLine, "material": p.Material,
			"colors": colors, "claims": confirmed, "drafts": pending, "conflicts": conf,
		})
	}
	pending, _ := s.ListPendingInbox()
	var inbox []map[string]any
	for _, it := range pending {
		inbox = append(inbox, InboxPublic(it))
	}
	if inbox == nil {
		inbox = []map[string]any{}
	}
	sum := s.Summary()
	return map[string]any{
		"rule":     "系统记住所有说法；人确认后才算数；冲突并存不覆盖；AI 只起草稿。收集箱图片先存着，等人叫 AI 再处理。",
		"products": products,
		"inbox":    inbox,
		"totals": map[string]any{
			"products":  sum["products"],
			"colors":    sum["colors"],
			"unopened":  sum["unopened"],
			"opened":    sum["opened"],
			"drafts":    drafts,
			"conflicts": conflicts,
			"inbox":     len(inbox),
		},
	}, nil
}

func (s *Store) SaveDrafts(in []Claim) ([]Claim, error) {
	var out []Claim
	for _, c := range in {
		c.Status = ClaimDraft
		saved, err := s.SaveClaim(c)
		if err != nil {
			return out, fmt.Errorf("%s: %w", c.Key, err)
		}
		out = append(out, saved)
	}
	if out == nil {
		out = []Claim{}
	}
	return out, nil
}
