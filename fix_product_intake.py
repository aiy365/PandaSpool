import re

with open('live_app.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the prompt-based intake with showIntakeModal
old_block = """      if (btn.dataset.intakec) {
        const cid = btn.dataset.intakec;
        const qStr = prompt("请输入要入库的盘数（将自动同步至拓竹云端）", "1");
        if (!qStr) return;
        const qty = parseInt(qStr, 10);
        if (isNaN(qty) || qty <= 0) { toast("数量不合法", "error"); return; }
        
        const oldText = btn.innerText;
        btn.innerText = "入库中...";
        btn.disabled = true;
        try {
          const spools = await api("/api/spools", { method: "POST", body: { color_id: cid, quantity: qty } });
          const codes = spools.map(s => s.short_code).join(", ");
          toast(`入库成功！短编号: ${codes}`, "success");
        } catch (ex) {
          toast(ex.message, "error");
        } finally {
          btn.innerText = oldText;
          btn.disabled = false;
        }
      }"""

new_block = """      if (btn.dataset.intakec) {
        window.showIntakeModal(btn.dataset.intakec);
      }"""

content = content.replace(old_block, new_block)

# Replace the delete confirm with confirmDanger
old_delc = """      if (btn.dataset.delc) {
        if (!confirm("删？")) return;
        try {
          await api("/api/colors/" + btn.dataset.delc, { method: "DELETE" });
          paint(me);
        } catch (ex) { toast(ex.message, "error"); }
      }"""

new_delc = """      if (btn.dataset.delc) {
        window.confirmDanger("确定要删除这个颜色吗？", async () => {
          try {
            await api("/api/colors/" + btn.dataset.delc, { method: "DELETE" });
            paint(me);
          } catch (ex) { toast(ex.message, "error"); }
        });
      }"""

content = content.replace(old_delc, new_delc)

with open('live_app.js', 'w', encoding='utf-8') as f:
    f.write(content)

print("Updated viewProduct button listeners.")
