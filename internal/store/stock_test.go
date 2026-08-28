package store

import (
	"testing"
)

func TestStockInAverage(t *testing.T) {
	dir := t.TempDir()
	st, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	p, err := st.SaveProduct(Product{Brand: "Polymaker", ProductLine: "Panchroma", Material: "PLA"})
	if err != nil {
		t.Fatal(err)
	}
	c, err := st.SaveColor(Color{ProductID: p.ID, Name: "白色"})
	if err != nil {
		t.Fatal(err)
	}
	apply := true
	if _, err := st.SaveStockIn(StockIn{ColorID: c.ID, Qty: 2, UnitPrice: 28, Apply: &apply}); err != nil {
		t.Fatal(err)
	}
	skip := false
	if _, err := st.SaveStockIn(StockIn{ColorID: c.ID, Qty: 1, UnitPrice: 22, Apply: &skip}); err != nil {
		t.Fatal(err)
	}
	cols, err := st.ListColors(p.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(cols) != 1 {
		t.Fatal(cols)
	}
	got := cols[0]
	if got.Unopened != 2 {
		t.Fatalf("unopened %d", got.Unopened)
	}
	if got.BuyQty != 3 {
		t.Fatalf("buy qty %v", got.BuyQty)
	}
	if got.AvgPrice < 25.9 || got.AvgPrice > 26.1 {
		t.Fatalf("avg %v want 26", got.AvgPrice)
	}
	u, o := applyInboundQty(0, 0, 1.5)
	if u != 1 || o != 1 {
		t.Fatalf("1.5 => %d+%d", u, o)
	}
}

func TestSaveColorUpsertsSameName(t *testing.T) {
	dir := t.TempDir()
	st, err := Open(dir)
	if err != nil {
		t.Fatal(err)
	}
	defer st.Close()
	p, err := st.SaveProduct(Product{Brand: "三绿", Material: "PLA"})
	if err != nil {
		t.Fatal(err)
	}
	a, err := st.SaveColor(Color{ProductID: p.ID, Name: "瓷白色", Unopened: 1})
	if err != nil {
		t.Fatal(err)
	}
	b, err := st.SaveColor(Color{ProductID: p.ID, Name: "瓷白色", Unopened: 3, Opened: 1})
	if err != nil {
		t.Fatal(err)
	}
	if a.ID != b.ID {
		t.Fatalf("same name should keep id %s vs %s", a.ID, b.ID)
	}
	cols, err := st.ListColors(p.ID)
	if err != nil {
		t.Fatal(err)
	}
	if len(cols) != 1 {
		t.Fatalf("want 1 color, got %d", len(cols))
	}
	if cols[0].Unopened != 3 || cols[0].Opened != 1 {
		t.Fatalf("updated stock %+v", cols[0])
	}
	e1, err := st.SaveColor(Color{ProductID: p.ID, Name: ""})
	if err != nil {
		t.Fatal(err)
	}
	e2, err := st.SaveColor(Color{ProductID: p.ID, Name: ""})
	if err != nil {
		t.Fatal(err)
	}
	if e1.ID == e2.ID {
		t.Fatal("empty names must stay distinct catalog slots")
	}
}
