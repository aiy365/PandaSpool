
import re

with open("web/dist/app.js", "r", encoding="utf-8") as f:
    text = f.read()

# Fix the dropped stk-stack class
text = text.replace(
    `<span class="stk-track"><span class="stk-fill" style="width:${pct}%">${segs}</span></span>`,
    `<span class="stk-track"><span class="stk-fill stk-stack" style="width:${pct}%">${segs}</span></span>`
)

with open("web/dist/app.js", "w", encoding="utf-8") as f:
    f.write(text)

with open("web/dist/styles.css", "r", encoding="utf-8") as f:
    css = f.read()

# Increase the label column width to fit the average price text
css = css.replace("grid-template-columns: 6.6rem 1fr 2rem;", "grid-template-columns: 9.5rem 1fr 2rem;")

with open("web/dist/styles.css", "w", encoding="utf-8") as f:
    f.write(css)

