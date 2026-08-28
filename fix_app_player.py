
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_play = """            const cam = await api("/api/camera");
            const ezW = document.getElementById("ezviz").clientWidth;
            const ezH = Math.round(ezW * 9 / 16);
            window.__ez = new window.EZUIKit.EZUIKitPlayer({ id: "ezviz", accessToken: cam.accessToken, url: cam.url, width: ezW, height: ezH });
            playBtn.textContent = "▶ 播放";"""

new_play = """            const cam = await api("/api/camera");
            const ezvizDiv = document.getElementById("ezviz");
            const ezW = ezvizDiv.clientWidth;
            const rot = d.ezviz?.rotation || "0";
            const isPortrait = (rot === "90" || rot === "-90");
            const finalH = isPortrait ? Math.round(ezW * 16 / 9) : Math.round(ezW * 9 / 16);
            
            ezvizDiv.style.height = finalH + "px";
            ezvizDiv.style.position = "relative";
            ezvizDiv.style.overflow = "hidden";
            
            const sub = document.createElement("div");
            sub.id = "ezviz-sub";
            ezvizDiv.appendChild(sub);
            
            const playerW = isPortrait ? finalH : ezW;
            const playerH = isPortrait ? ezW : finalH;
            
            window.__ez = new window.EZUIKit.EZUIKitPlayer({ id: "ezviz-sub", accessToken: cam.accessToken, url: cam.url, width: playerW, height: playerH });
            
            if (rot === "90") {
               sub.style.transform = "rotate(90deg)";
               sub.style.transformOrigin = "top left";
               sub.style.position = "absolute";
               sub.style.top = "0";
               sub.style.left = ezW + "px";
            } else if (rot === "-90") {
               sub.style.transform = "rotate(-90deg)";
               sub.style.transformOrigin = "top left";
               sub.style.position = "absolute";
               sub.style.top = finalH + "px";
               sub.style.left = "0";
            } else if (rot === "180") {
               sub.style.transform = "rotate(180deg)";
               sub.style.transformOrigin = "center center";
            }
            
            playBtn.textContent = "▶ 播放";"""

text = text.replace(old_play, new_play)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

