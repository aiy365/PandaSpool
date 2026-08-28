import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    js = f.read()

# 1. Dynamically set title in setup() or whenever page loads
# We can inject a function to update title
update_title = """
function updateAppTitle(title) {
  const displayTitle = title || "PandaSpool";
  document.title = displayTitle;
  const brandEl = document.querySelector(".navbar-center .btn-ghost");
  if (brandEl) brandEl.innerText = displayTitle;
  const brandMobileEl = document.querySelector(".drawer-side .text-2xl");
  if (brandMobileEl) brandMobileEl.innerText = displayTitle;
}
"""
if "function updateAppTitle" not in js:
    js = js.replace('async function api(', update_title + 'async function api(')

# In router logic or bootstrap fetch, call updateAppTitle
# In `init()` we fetch bootstrap data, which probably has site.title
old_init = """let bootstrapped = false;
async function init() {
  if (bootstrapped) return;
  try {
    const res = await api("/api/bootstrap");"""
new_init = """let bootstrapped = false;
let globalSettings = {};
async function init() {
  if (bootstrapped) return;
  try {
    const res = await api("/api/bootstrap");
    if (res && res.site) {
        updateAppTitle(res.site.title);
    }
    """
if "updateAppTitle(res.site.title);" not in js:
    js = js.replace(old_init, new_init)

# In settings render:
old_st_site = """${field("站点名称", inputEl("st-title", `value="${esc(data.site?.title||"")}"`))}"""
if "st-title" not in js:
    # We need to add the site title field to settings
    # Find `const { bambu` and insert before it
    old_st_render = """<div class="flex justify-between items-center mb-2">"""
    new_st_render = """<h2 class="card-title m-0 mb-4">基本设置</h2>
      <div class="row cols-1 mb-6">
        ${field("站点名称 (支持变量)", inputEl("st-title", `value="${esc(data.site?.title||"PandaSpool")}" placeholder="例如: PandaSpool / 我的耗材库"`))}
      </div>
      <div class="flex justify-between items-center mb-2">"""
    js = js.replace(old_st_render, new_st_render)

# In settings save:
old_st_save = """const payload = {
        bambu: {"""
new_st_save = """const payload = {
        site: { title: $("#st-title") ? $("#st-title").value.trim() : "PandaSpool" },
        bambu: {"""
if "site: { title:" not in js:
    js = js.replace(old_st_save, new_st_save)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(js)
