import fs from "node:fs";
import path from "node:path";
import vm from "node:vm";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const dir = path.dirname(fileURLToPath(import.meta.url));
const src = fs.readFileSync(path.join(dir, "../web/dist/stock-matrix.js"), "utf8");
const ctx = { console };
ctx.globalThis = ctx;
vm.runInNewContext(src, ctx);
const S = ctx.PPStock;

const whitePLA = [
  { brand: "Polymaker", product_line: "Panchroma", material: "PLA", colors: [{ name: "白色", color_family: "白色系", unopened: 2, opened: 0 }] },
  { brand: "Polymaker", product_line: "Panchroma Matte", material: "PLA", colors: [{ name: "棉花白", color_family: "白色系", unopened: 3, opened: 0 }] },
  { brand: "三绿", product_line: "", material: "PLA+2.0", colors: [{ name: "瓷白色", color_family: "白色系", unopened: 1, opened: 0 }] },
  { brand: "拓竹", product_line: "", material: "PLA Basic", colors: [{ name: "白色", color_family: "白色系", unopened: 1, opened: 1 }] },
  { brand: "拓竹", product_line: "Matte", material: "PLA Matte", colors: [{ name: "骨白色", color_family: "白色系", unopened: 1, opened: 0 }] },
  { brand: "彩多屋", product_line: "Silk", material: "PLA Silk", colors: [{ name: "珍珠白", color_family: "白色系", unopened: 1, opened: 0 }] },
];

assert.equal(S.materialBucket(whitePLA[1]), "PLA");
assert.equal(S.sliceKind(whitePLA[1]), "哑光");
assert.equal(S.sliceKind(whitePLA[3]), "普通");
assert.equal(S.materialBucket(whitePLA[5]), "PLA 丝绸");
assert.equal(S.sliceKind({ material: "PLA Lite", product_line: "Lite" }), "Lite");
assert.equal(S.materialBucket({ material: "PETG HF", product_line: "HF" }), "PETG");
assert.equal(S.sliceKind({ material: "PETG HF", product_line: "HF" }), "HF");
assert.equal(S.materialBucket({ material: "PETG Matte", product_line: "Matte" }), "PETG 哑光");

const m = S.buildStockMatrix(whitePLA);
const pla = m.cells.get("白色系\0PLA");
assert.equal(pla.n, 9);
assert.equal(pla.opened, 1);
assert.equal(pla.slices["普通"].n, 5);
assert.equal(pla.slices["普通"].opened, 1);
assert.equal(pla.slices["哑光"].n, 4);
assert.equal(pla.slices["Lite"], undefined);
assert.equal(m.cells.get("白色系\0PLA 丝绸").n, 1);
assert.equal(m.colSum["PLA"], 9);

const yellow = S.buildStockMatrix([
  { brand: "三绿", product_line: "Lite", material: "PLA Lite", colors: [{ name: "柠檬黄", color_family: "黄橙色系", unopened: 1, opened: 0 }] },
  { brand: "Polymaker", product_line: "Panchroma Matte", material: "PLA", colors: [{ name: "日落橙", color_family: "黄橙色系", unopened: 1, opened: 0 }] },
]);
const y = yellow.cells.get("黄橙色系\0PLA");
assert.equal(y.n, 2);
assert.equal(y.slices["Lite"].n, 1);
assert.equal(y.slices["哑光"].n, 1);

console.log("ok stock-matrix");
