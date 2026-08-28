
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_html = """      <p class="muted">层数 ${b.layer ?? "—"} / ${b.total_layer ?? "—"}　${esc(b.subtask || "")}</p>`;"""

new_html = """    let filamentStr = "";
    if (b.tray_now != null && String(b.tray_now) !== "255") {
      const tn = String(b.tray_now);
      if (tn === "254" && b.vt_tray) {
         filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${esc((b.vt_tray.tray_color || "888").substring(0,6))}]">料盘: ${esc(b.vt_tray.tray_type || "")} ${esc(b.vt_tray.tray_sub_brands || "")}</span>`;
      } else if (b.ams?.ams?.length > 0) {
         for (const a of b.ams.ams) {
            if (a.tray) {
               for (const t of a.tray) {
                  if (String(t.id) === tn) {
                     filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${esc((t.tray_color || "888").substring(0,6))}]">AMS-${tn}: ${esc(t.tray_type || "")} ${esc(t.tray_sub_brands || "")}</span>`;
                  }
               }
            }
         }
      }
    }
    const htmlPart = `<p class="muted">层数 ${b.layer ?? "—"} / ${b.total_layer ?? "—"}　${esc(b.subtask || "")}${filamentStr}</p>`;
"""
text = text.replace(old_html, new_html + "      " + old_html.replace("`<p class=\"muted\">层数 ${b.layer ?? \"—\"} / ${b.total_layer ?? \"—\"}　${esc(b.subtask || \"\")}</p>`;", "htmlPart;"))

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

