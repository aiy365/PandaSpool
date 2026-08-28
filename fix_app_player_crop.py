
import re
with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

old_play = """            ezvizDiv.style.height = finalH + "px";
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

new_play = """            const cropVals = (d.ezviz?.crop || "0,0,0,0").split(",").map(x => Number(x) || 0);
            const cT = Math.max(0, Math.min(99, cropVals[0]));
            const cB = Math.max(0, Math.min(99, cropVals[1]));
            const cL = Math.max(0, Math.min(99, cropVals[2]));
            const cR = Math.max(0, Math.min(99, cropVals[3]));
            const fW = 1 - (cL + cR) / 100;
            const fH = 1 - (cT + cB) / 100;
            
            const baseAspect = isPortrait ? 9/16 : 16/9;
            const cropAspect = baseAspect * (fW / fH);
            const displayH = Math.round(ezW / cropAspect);
            
            ezvizDiv.style.height = displayH + "px";
            ezvizDiv.style.position = "relative";
            ezvizDiv.style.overflow = "hidden";
            
            const cropWrapper = document.createElement("div");
            cropWrapper.style.position = "absolute";
            const uncroppedW = ezW / fW;
            const uncroppedH = displayH / fH;
            cropWrapper.style.width = uncroppedW + "px";
            cropWrapper.style.height = uncroppedH + "px";
            cropWrapper.style.left = - (cL / 100 * uncroppedW) + "px";
            cropWrapper.style.top = - (cT / 100 * uncroppedH) + "px";
            ezvizDiv.appendChild(cropWrapper);
            
            const rotWrapper = document.createElement("div");
            rotWrapper.style.position = "absolute";
            cropWrapper.appendChild(rotWrapper);
            
            const sub = document.createElement("div");
            sub.id = "ezviz-sub";
            rotWrapper.appendChild(sub);
            
            const playerW = isPortrait ? uncroppedH : uncroppedW;
            const playerH = isPortrait ? uncroppedW : uncroppedH;
            
            if (rot === "90") {
               rotWrapper.style.transform = "rotate(90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.left = uncroppedW + "px";
               rotWrapper.style.top = "0";
            } else if (rot === "-90") {
               rotWrapper.style.transform = "rotate(-90deg)";
               rotWrapper.style.transformOrigin = "top left";
               rotWrapper.style.width = playerW + "px";
               rotWrapper.style.height = playerH + "px";
               rotWrapper.style.top = uncroppedH + "px";
               rotWrapper.style.left = "0";
            } else if (rot === "180") {
               rotWrapper.style.transform = "rotate(180deg)";
               rotWrapper.style.transformOrigin = "center center";
               rotWrapper.style.width = "100%";
               rotWrapper.style.height = "100%";
               rotWrapper.style.left = "0";
               rotWrapper.style.top = "0";
            } else {
               rotWrapper.style.width = "100%";
               rotWrapper.style.height = "100%";
               rotWrapper.style.left = "0";
               rotWrapper.style.top = "0";
            }
            
            window.__ez = new window.EZUIKit.EZUIKitPlayer({ id: "ezviz-sub", accessToken: cam.accessToken, url: cam.url, width: playerW, height: playerH });"""

text = text.replace(old_play, new_play)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

