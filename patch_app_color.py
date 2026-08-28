
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """        let filamentStr = "";
        if (b.tray_now != null && String(b.tray_now) !== "255") {
          const tn = String(b.tray_now);
          if (tn === "254" && b.vt_tray) {
             filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${esc((b.vt_tray.tray_color || "888").substring(0,6))}]">料架: ${esc(getBrand(b.vt_tray))}</span>`;
          } else if (b.ams?.ams?.length > 0) {
             for (const a of b.ams.ams) {
                if (a.tray) {
                   for (const t of a.tray) {
                      if (String(t.id) === tn) {
                         filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${esc((t.tray_color || "888").substring(0,6))}]">AMS-${tn}: ${esc(getBrand(t))}</span>`;
                      }
                   }
                }
             }
          }
        }"""

new_code = """        let filamentStr = "";
        if (b.tray_now != null && String(b.tray_now) !== "255") {
          const tn = String(b.tray_now);
          if (tn === "254" && b.vt_tray) {
             const col = (b.vt_tray.tray_color || "888888").substring(0,6);
             filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${col}]">料架: [#${col}] ${esc(getBrand(b.vt_tray))}</span>`;
          } else if (b.ams?.ams?.length > 0) {
             for (const a of b.ams.ams) {
                if (a.tray) {
                   for (const t of a.tray) {
                      if (String(t.id) === tn) {
                         const col = (t.tray_color || "888888").substring(0,6);
                         filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${col}]">AMS-${tn}: [#${col}] ${esc(getBrand(t))}</span>`;
                      }
                   }
                }
             }
          }
        }"""

text = text.replace(old_code, new_code)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

