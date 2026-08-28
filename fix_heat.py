import re

with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

# Fix the heatmap colors by using DaisyUI's --p variable
css = css.replace("var(--color-primary)", "oklch(var(--p))")
css = css.replace("var(--color-base-200)", "var(--fallback-b2, oklch(var(--b2)))")
css = css.replace("var(--color-warning)", "oklch(var(--wa))")
css = css.replace("var(--color-primary-content)", "oklch(var(--pc))")
css = css.replace("var(--color-warning-content)", "oklch(var(--wac))")
css = css.replace("var(--color-base-content)", "var(--fallback-bc, oklch(var(--bc)))")

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)

with open('web/dist/stock-matrix.js', 'r', encoding='utf-8') as f:
    js = f.read()

# Update FAMILY_COLOR
old_colors = """  const FAMILY_COLOR = {
    "白色系": "#f8fafc",
    "黑色系": "#0f172a",
    "灰色系": "#64748b",
    "红粉色系": "#ef4444",
    "黄橙色系": "#f59e0b",
    "绿色系": "#22c55e",
    "蓝青色系": "#3b82f6",
    "紫棕色系": "#a855f7",
    "彩丝系": "#ec4899",
    "特殊色系": "#14b8a6",
  };
  const LIGHT_FAMS = ["白色系", "黄橙色系"];"""

new_colors = """  const FAMILY_COLOR = {
    "白色系": "#f8fafc",
    "黑灰色系": "#334155",
    "红粉色系": "#ef4444",
    "黄橙色系": "#f59e0b",
    "绿色系": "#22c55e",
    "蓝色系": "#3b82f6",
    "紫色系": "#a855f7",
    "棕米色系": "#b45309",
    "透明/自然色系": "#cbd5e1",
    "金属色系": "#64748b",
    "彩丝系": "#ec4899",
    "特殊色系": "#14b8a6",
  };
  const LIGHT_FAMS = ["白色系", "黄橙色系", "透明/自然色系"];"""

if old_colors in js:
    js = js.replace(old_colors, new_colors)
else:
    # If exact match fails, use regex or replace roughly
    pass

with open('web/dist/stock-matrix.js', 'w', encoding='utf-8') as f:
    f.write(js)
