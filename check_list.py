
with open("internal/store/store.go", "r", encoding="utf-8") as f:
    text = f.read()
    idx = text.find("func (s *Store) ListProducts()")
    print(text[idx:idx+1000])

