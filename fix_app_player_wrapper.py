
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_play = """            ezvizDiv.style.height = finalH + "px";
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
            }"""

new_play = """            ezvizDiv.style.height = finalH + "px";
            ezvizDiv.style.position = "relative";
            ezvizDiv.style.overflow = "hidden";
            
            const rotWrapper = document.createElement("div");
            rotWrapper.style.position = "absolute";
            rotWrapper.style.top = "0";
            rotWrapper.style.left = "0";
            rotWrapper.style.width = "100%";
            rotWrapper.style.height = "100%";
            ezvizDiv.appendChild(rotWrapper);
            
            const sub = document.createElement("div");
            sub.id = "ezviz-sub";
            rotWrapper.appendChild(sub);
            
            const playerW = isPortrait ? finalH : ezW;
            const playerH = isPortrait ? ezW : finalH;
            
            if (rot === "90") {
               rotWrapper.style.transform = "rotate(90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.left = ezW + "px";
            } else if (rot === "-90") {
               rotWrapper.style.transform = "rotate(-90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.top = finalH + "px";
            } else if (rot === "180") {
               rotWrapper.style.transform = "rotate(180deg)";
               rotWrapper.style.transformOrigin = "center center";
            }
            
            window.__ez = new window.EZUIKit.EZUIKitPlayer({ id: "ezviz-sub", accessToken: cam.accessToken, url: cam.url, width: playerW, height: playerH });"""

text = text.replace(old_play, new_play)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

