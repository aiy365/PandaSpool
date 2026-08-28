
const fs = require("fs");
const data = JSON.parse(fs.readFileSync("products.json"));
const brands = [...new Set((data || []).map((p) => p.brand).filter(Boolean))];
function productStock(p) {
  let unopened = 0, opened = 0;
  let shelf = [];
  if (p.colors) {
    p.colors.forEach((c) => {
      unopened += c.unopened;
      opened += c.opened;
      if (c.unopened > 0 || c.opened > 0) shelf.push(c);
    });
  }
  return { unopened, opened, shelf };
}
const filter = "shelf";
const query = "";
const brand = "";
const jumpBkt = "";
const jumpSlice = "";
const jumpFam = "";
function familyOf(c) { return c.color_family || "其他"; }
function colorOnShelf(c) { return c.unopened > 0 || c.opened > 0; }
function materialBucket(p) {
  const m = p.material.toUpperCase();
  if (m.includes("PLA")) return "PLA";
  if (m.includes("PETG")) return "PETG";
  if (m.includes("ABS") || m.includes("ASA")) return "ABS/ASA";
  if (m.includes("TPU")) return "TPU";
  return "其他";
}
function sliceKind(p) { return p.product_line || "标准"; }

try {
    const rows = (data || []).map((p) => ({ p, s: productStock(p) })).filter(({ p, s }) => {
      if (filter === "shelf" && s.shelf.length === 0) return false;
      if (brand && p.brand !== brand) return false;
      if (jumpBkt && materialBucket(p) !== jumpBkt) return false;
      if (jumpSlice && sliceKind(p) !== jumpSlice) return false;
      if (jumpFam) {
        const pool = filter === "shelf" ? s.shelf : (p.colors || []);
        if (!pool.some((c) => familyOf(c) === jumpFam && (filter !== "shelf" || colorOnShelf(c)))) return false;
      }
      if (!query) return true;
      const blob = [p.brand, p.product_line, p.material, ...(p.colors || []).map((c) => c.name)].join(" ").toLowerCase();
      return blob.includes(query);
    });
    console.log("Rows filtered OK. count =", rows.length);
} catch(e) {
    console.error(e);
}

