const fs = require('fs');
const src = fs.readFileSync('web/dist/stock-matrix.js', 'utf8');
const vm = require('vm');
const ctx = { console, globalThis: {} };
ctx.globalThis = ctx;
vm.runInNewContext(src, ctx);
const PPStock = ctx.PPStock;

try {
  const m = PPStock.buildStockMatrix([]);
  console.log("Empty:", Object.keys(m));
} catch(e) {
  console.error(e);
}
