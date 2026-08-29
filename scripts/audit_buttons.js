const fs = require('fs');
const src = fs.readFileSync('web/live_app.js', 'utf8');
const btnIds = [...src.matchAll(/<button[^>]*\sid="([a-z0-9-]+)"[^>]*>/gi)].map(m => m[1]);
const unique = [...new Set(btnIds)];
const missing = unique.filter(id => {
  const jq1 = "$('#" + id + "')";
  const jq2 = '$("#' + id + '")';
  const gebi = "getElementById('" + id + "')";
  return !src.includes(jq1) && !src.includes(jq2) && !src.includes(gebi);
});
console.log('静态按钮共', unique.length, '个');
console.log('无绑定的按钮:', missing.length ? missing.join(', ') : '无');
