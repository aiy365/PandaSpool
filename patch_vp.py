
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

text = text.replace("const p = data.product;", "const p = data.product || data;")
text = text.replace("const drafts = data.drafts || [];", "const drafts = data.drafts || data.product ? (data.drafts || []) : [];")
text = text.replace("const claims = data.claims || [];", "const claims = data.claims || data.product ? (data.claims || []) : [];")
text = text.replace("const conflictKeys = new Set((data.conflicts || []).map((c) => c.key));", "const conflictKeys = new Set((data.conflicts || []).map((c) => c.key));")

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

