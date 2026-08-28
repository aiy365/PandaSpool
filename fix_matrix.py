import re

with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    content = f.read()

# Make stk-table use collapse and border bottom
content = content.replace(
""".stk-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 4px;
  font-variant-numeric: tabular-nums;
}""",
""".stk-table {
  width: 100%;
  border-collapse: collapse;
  font-variant-numeric: tabular-nums;
}
.stk-table tbody tr {
  border-bottom: 1px solid var(--fallback-b3, oklch(var(--b3) / 0.3));
}
.stk-table tbody tr:hover td, .stk-table tbody tr:hover th {
  filter: brightness(0.95);
}
[data-theme="dark"] .stk-table tbody tr:hover td, [data-theme="dark"] .stk-table tbody tr:hover th {
  filter: brightness(1.2);
}"""
)

# Fix stk-cell border radius and margin
content = content.replace(
""".stk-cell {
  position: relative;
  text-align: center;
  min-width: 5.1rem;
  min-height: 3.4rem;
  padding: 0;
  border-radius: .55rem;
  cursor: pointer;
  vertical-align: middle;
  overflow: hidden;
}""",
""".stk-cell {
  position: relative;
  text-align: center;
  min-width: 5.1rem;
  min-height: 3.4rem;
  padding: 0;
  border: 1px solid var(--fallback-b1, oklch(var(--b1)));
  cursor: pointer;
  vertical-align: middle;
  overflow: hidden;
}"""
)

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated stk-table styles.")
