
with open("internal/server/server.go", "r", encoding="utf-8") as f:
    lines = f.readlines()
new_lines = []
in_import = False
seen = set()
for line in lines:
    if line.startswith("import ("):
        in_import = True
        new_lines.append(line)
        continue
    if in_import:
        if line.strip() == ")":
            in_import = False
            new_lines.append(line)
            continue
        pkg = line.strip().strip("\"")
        if pkg in seen or pkg == "":
            continue
        seen.add(pkg)
    new_lines.append(line)
with open("internal/server/server.go", "w", encoding="utf-8") as f:
    f.writelines(new_lines)

