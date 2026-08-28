
import re

with open("docs/PrintPilot缝合体_实用主义BOM_v3.md", "r", encoding="utf-8") as f:
    text = f.read()

new_row = "| **耗材重量称量** | **HX711 放大器 + 3kg平行梁称重传感器** | 扩展 | 放置于料盘底部，精确计算剩余耗材余量（空盘去皮），彻底解决余量焦虑。 |\n"

# We will inject this into the Chamber Air Node or make a new Filament Node.
# Since it mounts on the printer/spool holder, and Chamber Air Node ESP32-C3 has free pins (GPIO0, GPIO1), we can append it there.
text = text.replace("| **仓内漏粉监控** | **PMS5003** | 可选 | 监控耗材受潮拉丝、齿轮磨损导致的粉尘暴增。 |", "| **仓内漏粉监控** | **PMS5003** | 可选 | 监控耗材受潮拉丝、齿轮磨损导致的粉尘暴增。 |\n" + new_row)

with open("docs/PrintPilot缝合体_实用主义BOM_v3.md", "w", encoding="utf-8") as f:
    f.write(text)
print("Updated successfully")

