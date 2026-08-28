
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_sort = "rows.sort((a, b) => (b.s.unopened + b.s.opened) - (a.s.unopened + a.s.opened));"
new_sort = "rows.sort((a, b) => { const cmp = a.p.brand.localeCompare(b.p.brand); if (cmp !== 0) return cmp; return (b.s.unopened + b.s.opened) - (a.s.unopened + a.s.opened); });"

text = text.replace(old_sort, new_sort)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

