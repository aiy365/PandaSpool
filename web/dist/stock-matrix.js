globalThis.PPStock = (function() {
  const FAMILY_ORDER = [
    "白色系", "黑色系", "灰色系", "红粉色系", "黄橙色系", "绿色系", "蓝青色系", "紫棕色系", "彩丝系", "特殊色系"
  ];
  const BUCKET_ORDER = ["PLA", "PLA 丝绸", "PETG", "PETG 哑光", "ABS/ASA", "TPU", "特殊/其他"];
  const SLICE_ORDER = {
    "PLA": ["普通", "哑光", "Lite", "Meta"],
    "PETG": ["普通", "HF", "Trans", "ECO"],
  };
  const FAMILY_COLOR = {
    "白色系": "#f8fafc",
    "黑色系": "#0f172a",
    "灰色系": "#64748b",
    "红粉色系": "#ef4444",
    "黄橙色系": "#f59e0b",
    "绿色系": "#22c55e",
    "蓝青色系": "#3b82f6",
    "紫棕色系": "#a855f7",
    "彩丝系": "#ec4899",
    "特殊色系": "#14b8a6",
  };
  const LIGHT_FAMS = ["白色系", "黄橙色系"];

  const familyOf = (c) => c.color_family || "其他";
  
  const heatLevel = (n) => {
    if (!n) return 0;
    if (n < 2) return 1;
    if (n < 4) return 2;
    if (n < 8) return 3;
    return 4;
  };

  const materialBucket = (p) => {
    if (p.material.includes("Silk") || p.product_line.includes("Silk")) return "PLA 丝绸";
    if (p.material.includes("ABS") || p.material.includes("ASA")) return "ABS/ASA";
    if (p.material.includes("TPU")) return "TPU";
    if (p.product_line.includes("Matte") && p.material.includes("PETG")) return "PETG 哑光";
    if (p.material.includes("PETG")) return "PETG";
    if (p.material.includes("PLA")) return "PLA";
    return "特殊/其他";
  };

  const sliceKind = (p) => {
    if (p.product_line.includes("Matte")) return "哑光";
    if (p.product_line.includes("HF") || p.material.includes("HF")) return "HF";
    if (p.product_line.includes("Lite") || p.material.includes("Lite")) return "Lite";
    if (p.product_line.includes("Meta") || p.material.includes("Meta")) return "Meta";
    if (p.product_line.includes("ECO")) return "ECO";
    return "普通";
  };

  const buildStockMatrix = (products) => {
    const cells = new Map();
    const colSum = {};
    const rowSum = {};
    const famByBucket = {};
    let total = 0;

    for (const p of products || []) {
      const bucket = materialBucket(p);
      const kind = sliceKind(p);
      if (!colSum[bucket]) colSum[bucket] = 0;
      if (!famByBucket[bucket]) famByBucket[bucket] = {};

      for (const c of p.colors || []) {
        if (!c.unopened && !c.opened) continue;
        const count = (c.unopened || 0) + (c.opened || 0);
        if (count === 0) continue;

        const fam = familyOf(c);
        const key = fam + "\0" + bucket;
        
        if (!rowSum[fam]) rowSum[fam] = 0;
        if (!cells.has(key)) cells.set(key, { n: 0, opened: 0, slices: {}, bits: [] });
        
        const cell = cells.get(key);
        cell.n += count;
        cell.opened += (c.opened || 0);
        cell.bits.push({ name: c.name, n: count });
        
        if (!cell.slices[kind]) cell.slices[kind] = { n: 0, opened: 0, name: kind };
        cell.slices[kind].n += count;
        cell.slices[kind].opened += (c.opened || 0);
        
        colSum[bucket] += count;
        rowSum[fam] += count;
        total += count;
        
        famByBucket[bucket][fam] = (famByBucket[bucket][fam] || 0) + count;
      }
    }

    const fams = Object.keys(rowSum).sort((a, b) => {
      let idxA = FAMILY_ORDER.indexOf(a);
      let idxB = FAMILY_ORDER.indexOf(b);
      if (idxA === -1) idxA = 999;
      if (idxB === -1) idxB = 999;
      return idxA - idxB;
    });

    const buckets = Object.keys(colSum).sort((a, b) => {
      let idxA = BUCKET_ORDER.indexOf(a);
      let idxB = BUCKET_ORDER.indexOf(b);
      if (idxA === -1) idxA = 999;
      if (idxB === -1) idxB = 999;
      return idxA - idxB;
    });

    // ---- pla / petg / matte KPI stats ----
    let pla = 0, petg = 0, matte = 0;
    for (const b of Object.keys(colSum)) {
      if (b === "PLA") pla += colSum[b];
      if (b === "PETG") petg += colSum[b];
    }
    for (const [key, cell] of cells) {
      if (key.endsWith("\0PLA") && cell.slices["哑光"]) {
        matte += cell.slices["哑光"].n;
      }
    }
    matte += (colSum["PETG 哑光"] || 0);

    // ---- gaps: fam×bucket combos where both exist elsewhere but cell is empty ----
    const gaps = [];
    for (const f of fams) {
      for (const b of buckets) {
        if (!cells.has(f + "\0" + b)) {
          gaps.push({ f, b });
        }
      }
    }

    // ---- extra: non-empty cells sorted by count descending ----
    const extra = [];
    for (const [key, cell] of cells) {
      const [f, b] = key.split("\0");
      extra.push({ f, b, n: cell.n });
    }
    extra.sort((a, b) => b.n - a.n);

    // ---- singles: families with exactly 1 spool total ----
    const singles = fams.filter(f => rowSum[f] === 1);

    return { cells, colSum, rowSum, total, fams, buckets, famByBucket, pla, petg, matte, gaps, extra, singles };
  };

  return {
    FAMILY_ORDER, BUCKET_ORDER, SLICE_ORDER, FAMILY_COLOR, LIGHT_FAMS,
    materialBucket, sliceKind, familyOf, heatLevel, buildStockMatrix
  };
})();
