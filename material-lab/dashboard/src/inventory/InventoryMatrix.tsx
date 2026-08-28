import { useMemo } from "react";
import type { FilamentRow } from "./types";

const FAMILY_ORDER = [
  "白色系",
  "黑灰色系",
  "蓝色系",
  "绿色系",
  "红粉色系",
  "黄橙色系",
  "棕米色系",
  "紫色系",
  "金属色系",
  "透明/自然色系",
  "多色/效果色系",
  "未分类",
];

function productKey(row: FilamentRow): string {
  return `${row.brand || ""}\u0000${row.product_line || ""}\u0000${row.material_type || ""}`;
}

function stockLabel(row: FilamentRow): string {
  const sealed = row.stock_spools ? `封 ${row.stock_spools}` : "";
  const opened = row.opened_remaining_percent ? `开 ${row.opened_remaining_percent}%` : "";
  return [sealed, opened].filter(Boolean).join(" · ") || "无库存";
}

export function InventoryMatrix({
  rows,
  onInventory,
  onDetail,
}: {
  rows: FilamentRow[];
  onInventory: (row: FilamentRow) => void;
  onDetail: (row: FilamentRow) => void;
}) {
  const products = useMemo(() => {
    const seen = new Map<string, FilamentRow>();
    for (const row of rows) seen.set(productKey(row), row);
    return [...seen.entries()].sort(([, left], [, right]) =>
      `${left.brand} ${left.product_line}`.localeCompare(`${right.brand} ${right.product_line}`, "zh-CN"),
    );
  }, [rows]);

  const families = useMemo(() => {
    const grouped = new Map<string, string[]>();
    for (const row of rows) {
      const family = row.color_family || "未分类";
      const colors = grouped.get(family) || [];
      if (row.color && !colors.includes(row.color)) colors.push(row.color);
      grouped.set(family, colors);
    }
    return [...grouped.entries()]
      .sort(([left], [right]) => FAMILY_ORDER.indexOf(left) - FAMILY_ORDER.indexOf(right))
      .map(([family, colors]) => ({ family, colors: colors.sort((a, b) => a.localeCompare(b, "zh-CN")) }));
  }, [rows]);

  const cells = useMemo(() => {
    const index = new Map<string, FilamentRow>();
    for (const row of rows) index.set(`${productKey(row)}\u0000${row.color_family}\u0000${row.color}`, row);
    return index;
  }, [rows]);

  if (!rows.length) return null;

  return (
    <div className="inventory-matrix-shell">
      <div className="matrix-legend">
        <span><i className="matrix-dot sealed" />封：未开封整卷</span>
        <span><i className="matrix-dot opened" />开：当前一卷在用余量</span>
        <span>点击库存格进行盘点；右上角圆点表示已有商家资料</span>
      </div>
      <div className="inventory-matrix-scroll">
        <table className="inventory-matrix">
          <thead>
            <tr>
              <th className="matrix-sticky matrix-color-heading">色系 / 商家原色名</th>
              {products.map(([key, product]) => (
                <th key={key}>
                  <strong>{product.brand}</strong>
                  <span>{product.product_line}</span>
                  <small>{product.material_type}</small>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {families.flatMap(({ family, colors }) => [
              <tr className="matrix-family-row" key={`${family}-heading`}>
                <th className="matrix-sticky" colSpan={products.length + 1}>
                  <span>{family}</span><small>{colors.length} 个商家颜色名</small>
                </th>
              </tr>,
              ...colors.map((color) => (
                <tr key={`${family}-${color}`}>
                  <th className="matrix-sticky matrix-color-name">
                    <i data-family={family} />
                    <span>{color}</span>
                  </th>
                  {products.map(([key]) => {
                    const row = cells.get(`${key}\u0000${family}\u0000${color}`);
                    return (
                      <td key={`${key}-${family}-${color}`}>
                        {row ? (
                          <button className={`matrix-stock-cell ${row.opened_remaining_percent ? "has-opened" : ""}`} type="button" onClick={() => onInventory(row)} onContextMenu={(event) => { event.preventDefault(); onDetail(row); }} title="点击盘点；右键查看档案">
                            {row.source_count > 0 && <i className="matrix-source-dot" aria-label="已有商家资料" />}
                            <strong>{stockLabel(row)}</strong>
                            <small>{row.stock_equivalent.toFixed(row.stock_equivalent % 1 ? 1 : 0)} 卷当量</small>
                          </button>
                        ) : <span className="matrix-empty-cell">—</span>}
                      </td>
                    );
                  })}
                </tr>
              )),
            ])}
          </tbody>
        </table>
      </div>
    </div>
  );
}
