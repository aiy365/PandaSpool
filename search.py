
with open("internal/store/store.go", "r", encoding="utf-8") as f:
    lines = f.readlines()
    for i, line in enumerate(lines):
        if "GetProducts" in line:
            print("".join(lines[i:i+15]))
            break

