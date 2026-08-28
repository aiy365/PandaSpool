import re

with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

new_css = """
/* Visual Design Overhaul Overrides */

/* 1. Global Page Width & Alignment */
.page { max-width: 1100px; margin: 0 auto; width: 100%; padding: 1.5rem 1rem; }
.page-wide { max-width: 1400px; }
.topbar { justify-content: space-between; max-width: 1400px; margin: 0 auto; }

/* 2. Materials Grid Layout */
.inv-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}
.inv-card { margin-bottom: 0; display: flex; flex-direction: column; }

/* 3. Settings Masonry to Grid & Form Breathing Room */
.masonry-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.25rem;
  align-items: start;
}
.form-control { margin-bottom: 0.8rem; }
.form-control:last-child { margin-bottom: 0; }
.settings-head { display: flex; justify-content: flex-start; align-items: center; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.settings-head > div { flex: 1; }
.settings-head .btn-primary { margin-top: 0; }

/* 4. Stock Matrix Polish */
.stk-table thead th, .stk-foot td, .stk-foot th {
  background: var(--fallback-b2, oklch(var(--b2)));
  color: var(--fallback-bc, oklch(var(--bc)));
}
.stk-table thead th { border-bottom: 2px solid var(--fallback-b3, oklch(var(--b3) / 0.5)); }
.stk-foot th, .stk-foot td { border-top: 2px solid var(--fallback-b3, oklch(var(--b3) / 0.5)); font-weight: bold; }
.stk-zero { opacity: 0.25; font-size: 0.9rem; }
.stk-sum b { font-weight: 800; color: var(--color-base-content); }
[data-theme="dark"] .stk-sum b { color: #fff; }
"""

if "Visual Design Overhaul Overrides" not in content:
    content += new_css

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated styles.css with Design Overhaul.")
