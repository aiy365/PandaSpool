
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """        let filamentStr = "";
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
        }"""

new_code = """        const bmap = {
          "GFA00": "Bambu PLA Basic", "GFA01": "Bambu PLA Matte", "GFA02": "Bambu PLA Metal",
          "GFA03": "Bambu PLA Silk", "GFA04": "Bambu PLA Tough", "GFA05": "Bambu PLA Sparkle",
          "GFA07": "Bambu PLA Marble", "GFA08": "Bambu PLA Aero", "GFA09": "Bambu PLA CF",
          "GFA11": "Bambu PLA Galaxy", "GFB00": "Bambu PETG Basic", "GFB01": "Bambu PETG CF",
          "GFC00": "Bambu ABS", "GFC01": "Bambu ASA", "GFD00": "Bambu PC",
          "GFE00": "Bambu TPU 95A", "GFF00": "Bambu PVA", "GFG00": "Bambu PA-CF",
          "GFG01": "Bambu PA6-CF", "GFG50": "Bambu PAHT-CF", "GFU01": "Bambu Support G",
          "GFU02": "Bambu Support W"
        };
        const getBrand = (t) => {
          if (t.tray_sub_brands) return t.tray_sub_brands;
          if (t.tray_info_idx && bmap[t.tray_info_idx]) return bmap[t.tray_info_idx];
          return t.tray_type || "";
        };
        let filamentStr = "";
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

text = text.replace(old_code, new_code)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

