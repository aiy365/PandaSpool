
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_code = """        const getBrand = (t) => {
          if (t.tray_sub_brands) return t.tray_sub_brands;
          if (t.tray_info_idx && bmap[t.tray_info_idx]) return bmap[t.tray_info_idx];
          return t.tray_type || "";
        };
        let filamentStr = "";
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

new_code = """        const getBrand = (t) => {
          if (t.tray_sub_brands) return t.tray_sub_brands;
          if (t.tray_info_idx && bmap[t.tray_info_idx]) return bmap[t.tray_info_idx];
          return t.tray_type || "";
        };
        const getColorName = (hex) => {
          if (!hex || hex.length < 6) return "未知色";
          const r = parseInt(hex.substring(0, 2), 16), g = parseInt(hex.substring(2, 4), 16), b = parseInt(hex.substring(4, 6), 16);
          const colors = [
            {n:"白色",r:255,g:255,b:255}, {n:"黑色",r:0,g:0,b:0}, {n:"深灰",r:64,g:64,b:64}, {n:"浅灰",r:160,g:160,b:160},
            {n:"红色",r:255,g:0,b:0}, {n:"绿色",r:0,g:200,b:0}, {n:"蓝色",r:0,g:0,b:255}, {n:"黄色",r:255,g:255,b:0},
            {n:"橙色",r:255,g:128,b:0}, {n:"紫色",r:128,g:0,b:128}, {n:"粉色",r:255,g:192,b:203}, {n:"棕色",r:139,g:69,b:19},
            {n:"青色",r:0,g:255,b:255}, {n:"金色",r:218,g:165,b:32}, {n:"银色",r:192,g:192,b:192}, {n:"骨色/原色",r:227,g:218,b:201}
          ];
          let minDist = Infinity, closest = "未知";
          for (const c of colors) {
            const dist = (r-c.r)**2 + (g-c.g)**2 + (b-c.b)**2;
            if (dist < minDist) { minDist = dist; closest = c.n; }
          }
          return closest;
        };
        let filamentStr = "";
        if (b.tray_now != null && String(b.tray_now) !== "255") {
          const tn = String(b.tray_now);
          if (tn === "254" && b.vt_tray) {
             const col = (b.vt_tray.tray_color || "888888").substring(0,6);
             filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${col}]">料架: [${getColorName(col)}] ${esc(getBrand(b.vt_tray))}</span>`;
          } else if (b.ams?.ams?.length > 0) {
             for (const a of b.ams.ams) {
                if (a.tray) {
                   for (const t of a.tray) {
                      if (String(t.id) === tn) {
                         const col = (t.tray_color || "888888").substring(0,6);
                         filamentStr = `　<span class="badge badge-outline text-xs border-[color:#${col}]">AMS-${tn}: [${getColorName(col)}] ${esc(getBrand(t))}</span>`;
                      }
                   }
                }
             }
          }
        }"""

text = text.replace(old_code, new_code)
with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

