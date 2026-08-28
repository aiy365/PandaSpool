import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Restore renderApp
old_renderApp = """function renderApp(me) {
  root.innerHTML = "";
  root.append(h(`<div class="shell bg-base-200 min-h-screen pb-10">
    <header class="topbar navbar bg-base-100 shadow-sm mb-4 px-2 lg:px-4">
      <div class="navbar-start">
        <div class="dropdown">
          <div tabindex="0" role="button" class="btn btn-ghost lg:hidden">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" /></svg>
          </div>
          <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
            <li><a href="#/" data-p="/">总览</a></li>
            <li><a href="#/materials" data-p="/materials">耗材</a></li>
            <li><a href="#/spools" data-p="/spools">料盘</a></li>
            <li><a href="#/stock" data-p="/stock">盘点</a></li>
            <li><a href="#/compare" data-p="/compare">横评</a></li>
            <li><a href="#/machine" data-p="/machine">机台</a></li>
            <li><a href="#/air" data-p="/air">空气</a></li>
            <li><a href="#/settings" data-p="/settings">设置</a></li>
          </ul>
        </div>
        <span class="btn btn-ghost text-lg text-primary">${esc(me.title || "PrintPilot")}</span>
      </div>
      <div class="navbar-center hidden lg:flex">
        <ul class="menu menu-horizontal px-1">
          <li><a href="#/" data-p="/">总览</a></li>
          <li><a href="#/materials" data-p="/materials">耗材</a></li>
          <li><a href="#/spools" data-p="/spools">料盘</a></li>
          <li><a href="#/stock" data-p="/stock">盘点</a></li>
          <li><a href="#/compare" data-p="/compare">横评</a></li>
          <li><a href="#/machine" data-p="/machine">机台</a></li>
          <li><a href="#/air" data-p="/air">空气</a></li>
          <li><a href="#/settings" data-p="/settings">设置</a></li>
        </ul>
      </div>
      <div class="navbar-end gap-2">
        ${themeBtn()}
        <button class="btn btn-ghost btn-sm" id="out">退出</button>
      </div>
    </header>"""

new_renderApp = """function renderApp(me) {
  root.innerHTML = "";
  root.append(h(`<div class="shell bg-base-200">
    <header class="topbar">
      <!-- Mobile Nav -->
      <div class="dropdown nav-mobile">
        <div tabindex="0" role="button" class="btn btn-ghost">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h8m-8 6h16" /></svg>
        </div>
        <ul tabindex="0" class="menu menu-sm dropdown-content mt-3 z-[1] p-2 shadow bg-base-100 rounded-box w-52">
          <li><a href="#/" data-p="/">总览</a></li>
          <li><a href="#/materials" data-p="/materials">耗材</a></li>
          <li><a href="#/spools" data-p="/spools">料盘</a></li>
          <li><a href="#/stock" data-p="/stock">盘点</a></li>
          <li><a href="#/compare" data-p="/compare">横评</a></li>
          <li><a href="#/machine" data-p="/machine">机台</a></li>
          <li><a href="#/air" data-p="/air">空气</a></li>
          <li><a href="#/settings" data-p="/settings">设置</a></li>
        </ul>
      </div>
      
      <span class="btn btn-ghost text-lg text-primary">${esc(me.title || "PrintPilot")}</span>
      
      <!-- Desktop Nav -->
      <nav class="menu menu-horizontal px-1 nav-desktop">
        <li><a href="#/" data-p="/">总览</a></li>
        <li><a href="#/materials" data-p="/materials">耗材</a></li>
        <li><a href="#/spools" data-p="/spools">料盘</a></li>
        <li><a href="#/stock" data-p="/stock">盘点</a></li>
        <li><a href="#/compare" data-p="/compare">横评</a></li>
        <li><a href="#/machine" data-p="/machine">机台</a></li>
        <li><a href="#/air" data-p="/air">空气</a></li>
        <li><a href="#/settings" data-p="/settings">设置</a></li>
      </nav>
      
      <div class="grow"></div>
      ${themeBtn()}
      <button class="btn btn-ghost btn-sm" id="out">退出</button>
    </header>"""

if old_renderApp in content:
    content = content.replace(old_renderApp, new_renderApp)

# Restore viewSpools layout (I used missing tailwind classes like 'flex-col md:flex-row', 'md:w-64', 'hidden md:table-cell', etc)
# Let's fix those by using raw CSS or existing classes.
content = content.replace('class="flex flex-col md:flex-row md:items-center justify-between mb-4 gap-4"', 'style="display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem; margin-bottom: 1rem; align-items: center;"')
content = content.replace('class="flex flex-col md:flex-row gap-4 mb-4"', 'style="display: flex; flex-wrap: wrap; gap: 1rem; margin-bottom: 1rem;"')
content = content.replace('class="input input-bordered w-full md:w-64"', 'class="input input-bordered" style="flex: 1; min-width: 200px;"')
content = content.replace('class="tabs tabs-boxed overflow-x-auto whitespace-nowrap"', 'class="tabs tabs-boxed" style="flex-wrap: nowrap; overflow-x: auto;"')
content = content.replace('class="table table-zebra w-full table-sm md:table-md"', 'class="table table-zebra w-full"')
content = content.replace('class="hidden md:table-cell"', 'class="hide-on-mobile"')
content = content.replace('class="text-xs muted hidden md:table-cell"', 'class="text-xs muted hide-on-mobile"')
content = content.replace('class="font-bold text-sm md:text-base"', 'class="font-bold"')
content = content.replace('class="text-xs muted hidden md:block"', 'class="text-xs muted hide-on-mobile"')

# Restore settings and machine layouts (columns-1 lg:columns-2 gap-4 doesn't work)
# We will use .masonry-grid (and define it in styles.css)
content = content.replace('<div class="columns-1 lg:columns-2 gap-4">', '<div class="masonry-grid">')
content = content.replace('<div class="columns-1 md:columns-2 gap-4">', '<div class="masonry-grid">')
content = content.replace('class="card bg-base-100 shadow-sm border border-base-300 break-inside-avoid mb-4"', 'class="card bg-base-100 shadow-sm border border-base-300 masonry-item"')

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

# Update styles.css
with open('web/dist/styles.css', 'r', encoding='utf-8') as f:
    css = f.read()

new_css_rules = """
/* Mobile specific utility classes */
@media (min-width: 800px) {
  .nav-mobile { display: none !important; }
}
@media (max-width: 799px) {
  .nav-desktop { display: none !important; }
  .hide-on-mobile { display: none !important; }
  .topbar { padding: 0.2rem 0.5rem; }
  .masonry-grid { column-count: 1 !important; }
}
.masonry-grid {
  column-count: 2;
  column-gap: 1rem;
}
@media (min-width: 1200px) {
  .masonry-grid { column-count: 3; }
}
.masonry-item {
  break-inside: avoid;
  margin-bottom: 1rem;
}
"""

if "nav-mobile" not in css:
    css += new_css_rules

with open('web/dist/styles.css', 'w', encoding='utf-8') as f:
    f.write(css)

print("Restored UI and injected custom responsive CSS.")
