
import os
for root, dirs, files in os.walk("internal/store"):
    for file in files:
        if file.endswith(".go"):
            with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                for line in f:
                    if "GetProducts" in line:
                        print(f"{file}: {line.strip()}")

