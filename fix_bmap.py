
import os

corrected_bmap = """        const bmap = {
          "GFA00": "Bambu PLA Basic", "GFA01": "Bambu PLA Matte", "GFA02": "Bambu PLA Metal",
          "GFA03": "Bambu PLA Silk", "GFA04": "Bambu PLA Tough", "GFA05": "Bambu PLA Sparkle",
          "GFA07": "Bambu PLA Marble", "GFA08": "Bambu PLA Aero", "GFA09": "Bambu PLA CF",
          "GFA11": "Bambu PLA Galaxy", "GFB00": "Bambu ABS", "GFB01": "Bambu ASA",
          "GFC00": "Bambu PC", "GFC01": "Bambu PC", 
          "GFE00": "Bambu TPU 95A", "GFF00": "Bambu PVA", 
          "GFG00": "Bambu PETG Basic", "GFG50": "Bambu PETG-CF",
          "GFN03": "Bambu PA-CF", "GFN04": "Bambu PAHT-CF", "GFN05": "Bambu PA6-CF",
          "GFU01": "Bambu Support G", "GFU02": "Bambu Support W"
        };"""

def patch_file(filepath):
    if not os.path.exists(filepath): return
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # We will just replace the whole const bmap = { ... };
    import re
    # Find the const bmap = { ... }; block
    pattern = r"const bmap = \{.*?\};"
    new_content = re.sub(pattern, corrected_bmap.strip(), content, flags=re.DOTALL)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Patched {filepath}")

patch_file("web/dist/app.js")
patch_file("live_app.js")

