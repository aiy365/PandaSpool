import re
with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

css = css.replace("var(--fallback-b2, oklch(var(--b2)))", "oklch(var(--b2))")
css = css.replace("var(--fallback-bc, oklch(var(--bc)))", "oklch(var(--bc))")

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)
