package store

import (
	"os"
	"path/filepath"
	"testing"
)

func TestClassifyColorFamily(t *testing.T) {
	if ClassifyColorFamily("土壤棕") != "棕米色系" {
		t.Fatal(ClassifyColorFamily("土壤棕"))
	}
	if ClassifyColorFamily("拿铁色") != "棕米色系" {
		t.Fatal(ClassifyColorFamily("拿铁色"))
	}
	if ClassifyColorFamily("浅褐色") != "棕米色系" {
		t.Fatal(ClassifyColorFamily("浅褐色"))
	}
	if ClassifyColorFamily("杏色") != "棕米色系" {
		t.Fatal(ClassifyColorFamily("杏色"))
	}
	if ClassifyColorFamily("深橄榄色") != "绿色系" {
		t.Fatal(ClassifyColorFamily("深橄榄色"))
	}
	if ClassifyColorFamily("电光蓝") != "蓝色系" {
		t.Fatal(ClassifyColorFamily("电光蓝"))
	}
	if ClassifyColorFamily("") != "未分类" {
		t.Fatal("empty")
	}
}

func TestConflictsAndNoOverwrite(t *testing.T) {
	dir := t.TempDir()
	st, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	p, err := st.SaveProduct(Product{Brand: "R3D", ProductLine: "PETG", Material: "PETG"})
	if err != nil {
		t.Fatal(err)
	}
	a, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "厂家", Key: "喷嘴温度", Value: "230-260", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	if a.Source != "资料" {
		t.Fatalf("厂家 should collapse to 资料, got %q", a.Source)
	}
	asMerchant, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "商家", Key: "喷嘴温度", Value: "230-260", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	if asMerchant.ID != a.ID {
		t.Fatal("厂家 and 商家 are the same source")
	}
	b, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "实测", Key: "喷嘴温度", Value: "240", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	if a.ID == b.ID {
		t.Fatal("different sayings must be two rows")
	}
	if a.Key != "喷嘴温度范围" {
		t.Fatalf("range key %q", a.Key)
	}
	if b.Key != "喷嘴实测温度" {
		t.Fatalf("measured key %q", b.Key)
	}
	again, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "资料", Key: "喷嘴温度", Value: "230-260", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	if again.ID != a.ID {
		t.Fatal("same saying should be idempotent")
	}
	if n := ConflictsOf([]Claim{a, b}); len(n) != 0 {
		t.Fatalf("range vs measured must not conflict: %+v", n)
	}
	rec, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "资料", Key: "喷嘴推荐温度", Value: "250", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	other, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "资料", Key: "喷嘴推荐温度", Value: "240", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	conf := ConflictsOf([]Claim{rec, other})
	if len(conf) != 1 || conf[0].Key != "喷嘴推荐温度" {
		t.Fatalf("%+v", conf)
	}
	d, err := st.SaveClaim(Claim{ProductID: p.ID, Source: "资料", Key: "热床", Value: "80", Unit: "°C", Status: ClaimDraft})
	if err != nil {
		t.Fatal(err)
	}
	if d.Status != ClaimDraft {
		t.Fatal(d.Status)
	}
	if err := st.SetClaimStatus(d.ID, ClaimConfirmed); err != nil {
		t.Fatal(err)
	}
	pack, err := st.AIPack()
	if err != nil {
		t.Fatal(err)
	}
	totals := pack["totals"].(map[string]any)
	if totals["conflicts"].(int) != 1 {
		t.Fatalf("conflicts %v", totals["conflicts"])
	}
	cWhite, err := st.SaveColor(Color{ProductID: p.ID, Name: "白色"})
	if err != nil {
		t.Fatal(err)
	}
	cBlack, err := st.SaveColor(Color{ProductID: p.ID, Name: "黑色"})
	if err != nil {
		t.Fatal(err)
	}
	w, err := st.SaveClaim(Claim{ProductID: p.ID, ColorID: cWhite.ID, Source: "实测", Key: "喷嘴实测温度", Value: "220", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	k, err := st.SaveClaim(Claim{ProductID: p.ID, ColorID: cBlack.ID, Source: "实测", Key: "喷嘴实测温度", Value: "235", Unit: "°C"})
	if err != nil {
		t.Fatal(err)
	}
	if n := ConflictsOf([]Claim{w, k}); len(n) != 0 {
		t.Fatalf("different colors must not conflict: %+v", n)
	}
	_ = os.RemoveAll(filepath.Join(dir, "app.sqlite3"))
}

func TestReclassifyUnsetFamilies(t *testing.T) {
	dir := t.TempDir()
	st, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	p, err := st.SaveProduct(Product{Brand: "大简", ProductLine: "HF", Material: "PETG HF"})
	if err != nil {
		t.Fatal(err)
	}
	c, err := st.SaveColor(Color{ProductID: p.ID, Name: "拿铁色", ColorFamily: "未分类", Unopened: 1})
	if err != nil {
		t.Fatal(err)
	}
	if err := st.reclassifyUnsetFamilies(); err != nil {
		t.Fatal(err)
	}
	got, err := st.ListColors(p.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(got) != 1 || got[0].ID != c.ID || got[0].ColorFamily != "棕米色系" {
		t.Fatalf("%+v", got)
	}
}

func TestInboxDedup(t *testing.T) {
	dir := t.TempDir()
	st, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	p, err := st.SaveProduct(Product{Brand: "R3D", ProductLine: "PETG", Material: "PETG"})
	if err != nil {
		t.Fatal(err)
	}
	png := []byte{0x89, 'P', 'N', 'G', '\r', '\n', 0x1a, '\n', 1, 2, 3, 4}
	a, err := st.SaveInboxFile(p.ID, "", "a.png", png)
	if err != nil {
		t.Fatal(err)
	}
	b, err := st.SaveInboxFile(p.ID, "", "b.png", png)
	if err != nil {
		t.Fatal(err)
	}
	if a.ID != b.ID {
		t.Fatal("same image should dedup")
	}
	if DetectImageMIME(png) != "image/png" {
		t.Fatal(DetectImageMIME(png))
	}
	if _, err := st.SaveInboxFile(p.ID, "", "x.bin", []byte("nope")); err == nil {
		t.Fatal("non-image should fail")
	}
}
