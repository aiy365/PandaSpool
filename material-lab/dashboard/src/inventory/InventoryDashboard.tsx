import { ArrowsClockwise } from "@phosphor-icons/react/ArrowsClockwise";
import { ArrowCounterClockwise } from "@phosphor-icons/react/ArrowCounterClockwise";
import { Check } from "@phosphor-icons/react/Check";
import { Columns } from "@phosphor-icons/react/Columns";
import { FloppyDisk } from "@phosphor-icons/react/FloppyDisk";
import { GearSix } from "@phosphor-icons/react/GearSix";
import { GridFour } from "@phosphor-icons/react/GridFour";
import { List } from "@phosphor-icons/react/List";
import { ListBullets } from "@phosphor-icons/react/ListBullets";
import { MagnifyingGlass } from "@phosphor-icons/react/MagnifyingGlass";
import { Package } from "@phosphor-icons/react/Package";
import { PencilSimple } from "@phosphor-icons/react/PencilSimple";
import { Plus } from "@phosphor-icons/react/Plus";
import { ShoppingCart } from "@phosphor-icons/react/ShoppingCart";
import { Power } from "@phosphor-icons/react/Power";
import { Scales } from "@phosphor-icons/react/Scales";
import { Sparkle } from "@phosphor-icons/react/Sparkle";
import { SignOut } from "@phosphor-icons/react/SignOut";
import { Stack } from "@phosphor-icons/react/Stack";
import { Table } from "@phosphor-icons/react/Table";
import { Trash } from "@phosphor-icons/react/Trash";
import { WarningCircle } from "@phosphor-icons/react/WarningCircle";
import { X } from "@phosphor-icons/react/X";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  TabulatorFull as Tabulator,
  type CellComponent,
  type ColumnDefinition,
  type ColumnLayout,
  type Filter,
  type Sorter,
} from "tabulator-tables";
import { DashboardApiError, dashboardApi, userMessage, type SessionInfo } from "./api";
import type {
  DashboardPayload,
  EvidenceCreateInput,
  FilamentCreateInput,
  FilamentDetail,
  FilamentUpdateInput,
  FilamentRow,
  InventorySetInput,
  ImageRecognitionResult,
  SavedView,
  AiInventoryPacket,
  ProductCatalogPayload,
  ProductDetail,
  ProductEvidenceCreateInput,
  ProductSummary,
  ProductPresetCreateInput,
} from "./types";
import { InventoryMatrix } from "./InventoryMatrix";
import {
  DEFAULT_VIEWS,
  FIELD_LABELS,
  FIELD_ORDER,
  loadActiveView,
  loadViews,
  resetViews,
  saveActiveView,
  saveViews,
} from "./viewStore";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";

const EMPTY_PAYLOAD: DashboardPayload = {
  rows: [],
  summary: { filament_count: 0, stock_spools: 0, opened_spool_count: 0, stock_equivalent: 0, product_series_count: 0, color_variant_count: 0, unclassified_color_count: 0, stock_total_kg: 0, low_stock_count: 0, replenishment_spools: 0, needs_attention_count: 0 },
};
const EMPTY_PRODUCTS: ProductCatalogPayload = {
  rows: [],
  summary: { product_count: 0, color_count: 0, stock_equivalent: 0, manufacturer_preset_count: 0 },
};

const MATERIAL_OPTIONS = ["PLA", "PETG", "ABS", "ASA", "TPU", "PA", "PC", "PCTG", "PP", "PVA", "HIPS", "PET"];
const REGION_OPTIONS = [
  ["CN", "中国大陆"], ["Global", "全球"], ["US", "美国"], ["EU", "欧洲"], ["JP", "日本"], ["Other", "其他"],
] as const;
const STATUS_OPTIONS = [
  ["staged", "待审核"], ["reviewed", "已审核"], ["calibrated", "已校准"], ["archived", "已归档"],
] as const;
const COMMON_COLORS = ["透明", "白色", "黑色", "灰色", "银色", "红色", "橙色", "黄色", "绿色", "蓝色", "紫色", "棕色", "自然色"];
const COLOR_FAMILIES = ["白色系", "黑灰色系", "蓝色系", "绿色系", "红粉色系", "黄橙色系", "棕米色系", "紫色系", "金属色系", "透明/自然色系", "多色/效果色系", "未分类"];
const CLAIM_OPTIONS = [
  ["available_colors", "系列颜色目录"],
  ["diameter", "线径"],
  ["diameter_tolerance", "线径公差"],
  ["spool_weight", "单卷净重"],
  ["spool_weight_tolerance", "净重公差"],
  ["nozzle_temperature", "喷嘴温度"],
  ["bed_temperature", "热床温度"],
  ["cooling_fan", "冷却风扇"],
  ["print_speed", "打印速度"],
  ["drying_temperature", "烘干温度"],
  ["drying_time", "烘干时间"],
  ["retraction_distance", "回抽距离"],
  ["retraction_speed", "回抽速度"],
  ["nozzle_compatibility", "喷嘴兼容性"],
  ["build_surface", "底板/打印面"],
  ["density", "密度"],
  ["heat_deflection_temperature", "热变形温度"],
  ["melt_flow_index", "熔融指数"],
  ["vicat_softening_temperature", "维卡软化温度"],
  ["tensile_strength", "拉伸强度"],
  ["tensile_modulus", "拉伸/杨氏模量"],
  ["elongation_at_break", "断裂伸长率"],
  ["flexural_strength", "弯曲强度"],
  ["flexural_modulus", "弯曲模量"],
  ["notched_impact_strength", "缺口冲击强度"],
  ["unnotched_impact_strength", "无缺口冲击强度"],
  ["shore_hardness", "邵氏硬度"],
  ["water_absorption", "吸水率"],
  ["seller_price", "销售价格（时效信息）"],
  ["customer_quote", "客服/商家原话"],
  ["source_note", "资料原文备注"],
] as const;
const SOURCE_KIND_OPTIONS = [
  ["manufacturer", "厂家资料"],
  ["seller", "销售页面"],
  ["customer_service", "客服回复"],
  ["official_profile", "官方预设"],
  ["user_note", "个人记录"],
] as const;
const SOURCE_DECISION_OPTIONS = [
  ["undecided", "未决定"],
  ["use_default_profile", "直接使用默认参数"],
  ["reference_only", "仅作参考"],
  ["needs_validation", "待验证"],
] as const;

function sourceKindLabel(kind: string): string {
  return SOURCE_KIND_OPTIONS.find(([value]) => value === kind)?.[1] || kind;
}

function claimKeyLabel(key: string): string {
  return CLAIM_OPTIONS.find(([value]) => value === key)?.[1] || key;
}

function claimValueText(value: unknown): string {
  if (Array.isArray(value)) return value.map(String).join("、");
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function claimColors(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String).filter(Boolean);
  if (typeof value !== "string") return [];
  return value.split(/[,，、;；\n]+/).map((item) => item.trim()).filter(Boolean);
}

type NumericRange = { min: number; max: number };
type PresetComparison = {
  id: string;
  label: string;
  claimValue: string;
  presetValue: string;
  presetName: string;
  conflict: boolean;
};

function numericRange(value: unknown): NumericRange | null {
  if (Array.isArray(value) && value.length === 1) return numericRange(value[0]);
  if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    const min = Number(record.min);
    const max = Number(record.max);
    if (Number.isFinite(min) && Number.isFinite(max)) return { min: Math.min(min, max), max: Math.max(min, max) };
    const center = Number(record.value);
    const tolerance = Number(record.tolerance);
    if (Number.isFinite(center) && Number.isFinite(tolerance)) return { min: center - tolerance, max: center + tolerance };
  }
  const text = String(value ?? "").trim();
  const numbers = [...text.matchAll(/\d+(?:\.\d+)?/g)].map((match) => Number(match[0]));
  if (!numbers.length) return null;
  if (text.includes("±") && numbers.length >= 2) return { min: numbers[0] - numbers[1], max: numbers[0] + numbers[1] };
  if (numbers.length >= 2) return { min: Math.min(numbers[0], numbers[1]), max: Math.max(numbers[0], numbers[1]) };
  return { min: numbers[0], max: numbers[0] };
}

function presetRanges(claimKey: string, settings: Record<string, unknown>): NumericRange[] {
  if (claimKey === "nozzle_temperature") {
    const low = numericRange(settings.nozzle_temperature_range_low);
    const high = numericRange(settings.nozzle_temperature_range_high);
    if (low && high) return [{ min: low.min, max: high.max }];
    return [numericRange(settings.nozzle_temperature)].filter(Boolean) as NumericRange[];
  }
  if (claimKey === "bed_temperature") {
    return ["hot_plate_temp", "textured_plate_temp", "eng_plate_temp", "cool_plate_temp"]
      .map((key) => numericRange(settings[key])).filter(Boolean) as NumericRange[];
  }
  if (claimKey === "cooling_fan") {
    const low = numericRange(settings.fan_min_speed);
    const high = numericRange(settings.fan_max_speed);
    return low && high ? [{ min: low.min, max: high.max }] : [];
  }
  if (claimKey === "density") return [numericRange(settings.filament_density)].filter(Boolean) as NumericRange[];
  return [];
}

function compareClaimsToPresets(claims: ProductDetail["product_claims"], presets: ProductDetail["presets"]): PresetComparison[] {
  const rows: PresetComparison[] = [];
  for (const preset of presets) {
    for (const claim of claims.filter((item) => item.review_status !== "rejected")) {
      const claimed = numericRange(claim.value);
      const expected = presetRanges(claim.claim_key, preset.settings);
      if (!claimed || !expected.length) continue;
      const matches = expected.some((range) => claimed.min <= range.max && claimed.max >= range.min);
      rows.push({
        id: `${preset.id}-${claim.id}`,
        label: claimKeyLabel(claim.claim_key),
        claimValue: `${claimValueText(claim.value)}${claim.unit ? ` ${claim.unit}` : ""}`,
        presetValue: expected.map((range) => range.min === range.max ? String(range.min) : `${range.min}–${range.max}`).join(" / "),
        presetName: preset.profile_name,
        conflict: !matches,
      });
    }
  }
  return rows;
}

function sourceDecisionLabel(decision: string): string {
  return SOURCE_DECISION_OPTIONS.find(([value]) => value === decision)?.[1] || decision;
}

const textColumn = (title: string, field: string, width = 150): ColumnDefinition => ({
  title,
  field,
  width,
  minWidth: 110,
  headerFilter: "input",
  headerFilterPlaceholder: "筛选",
  tooltip: true,
});

function dateFormatter(cell: CellComponent): string {
  const value = cell.getValue();
  if (!value) return "—";
  const date = new Date(String(value));
  if (Number.isNaN(date.valueOf())) return "—";
  return new Intl.DateTimeFormat("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}

function statusFormatter(cell: CellComponent): HTMLElement {
  const value = String(cell.getValue() || "—");
  const badge = document.createElement("span");
  badge.className = `status-badge status-${value === "正常" ? "normal" : value === "低库存" ? "low" : "empty"}`;
  badge.textContent = value;
  return badge;
}

function matchesSearch(row: FilamentRow, search: string): boolean {
  const needle = search.trim().toLocaleLowerCase("zh-CN");
  if (!needle) return true;
  return [row.brand, row.product_line, row.material_type, row.color, row.color_family, row.variant, row.sku, row.storage_location]
    .filter(Boolean).some((value) => String(value).toLocaleLowerCase("zh-CN").includes(needle));
}

function colorPreview(color: string | null): string {
  const value = (color || "").toLocaleLowerCase("zh-CN");
  const colors: Array<[string[], string]> = [
    [["黑", "black"], "#18181b"], [["白", "white"], "#fafafa"], [["灰", "gray", "grey"], "#a1a1aa"],
    [["红", "red"], "#dc2626"], [["橙", "orange"], "#ea580c"], [["黄", "yellow"], "#eab308"],
    [["绿", "green"], "#16a34a"], [["蓝", "blue"], "#2563eb"], [["紫", "purple"], "#9333ea"],
    [["棕", "brown"], "#92400e"], [["透明", "clear", "transparent"], "#f1f5f9"],
  ];
  return colors.find(([keys]) => keys.some((key) => value.includes(key)))?.[1] || "#cbd5e1";
}

function nextActionFor(row: FilamentRow): string {
  if (row.stock_equivalent === 0) return "当前没有库存，请先完成盘点。";
  if (row.opened_remaining_percent > 0) return `当前有一卷已开封，估计余量${row.opened_remaining_percent}%，下次盘点优先核对。`;
  if (row.source_count === 0) return "还没有商家资料；可上传参数图或记录客服原话。";
  if (row.conflict_count > 0) return "先核对厂家资料中的冲突字段，不要直接合并成一个参数。";
  return "库存和商家资料已建档，后续只需按实际情况盘点。";
}

function makeColumns(onAction: (action: string, row: FilamentRow) => void): ColumnDefinition[] {
  return [
    textColumn("品牌", "brand", 120),
    textColumn("制造商", "manufacturer", 150),
    textColumn("销售商", "seller", 140),
    textColumn("产品线", "product_line", 190),
    textColumn("材料", "material_type", 110),
    textColumn("型号", "variant", 150),
    textColumn("颜色", "color", 120),
    textColumn("色系", "color_family", 130),
    { title: "线径（毫米）", field: "diameter_mm", width: 125, hozAlign: "right", sorter: "number" },
    textColumn("SKU", "sku", 160),
    textColumn("条码", "barcode", 170),
    textColumn("地区", "region", 90),
    textColumn("档案状态", "status", 115),
    {
      title: "未开封（卷）",
      field: "stock_spools",
      width: 112,
      hozAlign: "right",
      sorter: "number",
      cssClass: "stock-cell",
    },
    {
      title: "在用卷余量（%）",
      field: "opened_remaining_percent",
      width: 140,
      hozAlign: "right",
      sorter: "number",
    },
    {
      title: "库存当量（卷）",
      field: "stock_equivalent",
      width: 135,
      hozAlign: "right",
      sorter: "number",
    },
    {
      title: "单卷净重（克）",
      field: "spool_weight_g",
      width: 145,
      hozAlign: "right",
      sorter: "number",
    },
    {
      title: "总重量（千克）",
      field: "stock_total_kg",
      width: 145,
      hozAlign: "right",
      sorter: "number",
      formatter: (cell) => Number(cell.getValue() || 0).toFixed(3),
    },
    {
      title: "低库存阈值",
      field: "low_stock_threshold",
      width: 125,
      hozAlign: "right",
      sorter: "number",
    },
    { title: "目标库存（卷）", field: "target_stock_spools", width: 130, hozAlign: "right", sorter: "number" },
    { title: "待补货（卷）", field: "replenishment_spools", width: 120, hozAlign: "right", sorter: "number" },
    textColumn("存放位置", "storage_location", 140),
    textColumn("库存备注", "inventory_notes", 180),
    {
      title: "库存状态",
      field: "stock_status",
      width: 118,
      formatter: statusFormatter,
    },
    { title: "商家资料", field: "source_count", width: 105, hozAlign: "right", sorter: "number" },
    { title: "冲突项", field: "conflict_count", width: 90, hozAlign: "right", sorter: "number" },
    { title: "建档时间", field: "created_at", width: 175, formatter: dateFormatter },
    {
      title: "库存更新时间",
      field: "inventory_updated_at",
      width: 175,
      formatter: dateFormatter,
    },
    textColumn("耗材ID", "filament_id", 285),
    {
      title: "库存操作",
      field: "_actions",
      width: 210,
      minWidth: 210,
      frozen: true,
      headerSort: false,
      formatter: () =>
        '<div class="row-actions"><button type="button" data-action="edit">编辑</button><button type="button" data-action="increment">+1 入库</button><button type="button" data-action="set">盘点</button></div>',
      cellClick: (event, cell) => {
        const button = (event.target as HTMLElement).closest<HTMLButtonElement>("button[data-action]");
        if (button) onAction(button.dataset.action || "", cell.getRow().getData() as FilamentRow);
      },
    },
  ];
}

function makeDefaultLayout(table: Tabulator, view: SavedView): ColumnLayout[] {
  const base = table.getColumnLayout();
  const byField = new Map(base.map((column) => [column.field, column]));
  const ordered = [
    ...view.visibleFields,
    ...FIELD_ORDER.filter((field) => !view.visibleFields.includes(field)),
    "_actions",
  ];
  return ordered
    .map((field) => byField.get(field))
    .filter((column): column is ColumnLayout => Boolean(column))
    .map((column) => ({
      ...column,
      visible: column.field === "_actions" || view.visibleFields.includes(column.field || ""),
    }));
}

function InventoryDialog({
  row,
  busy,
  onClose,
  onSubmit,
}: {
  row: FilamentRow;
  busy: boolean;
  onClose: () => void;
  onSubmit: (input: InventorySetInput) => void;
}) {
  const [spools, setSpools] = useState(String(row.stock_spools));
  const [opened, setOpened] = useState(String(row.opened_remaining_percent));
  const [weight, setWeight] = useState(String(row.spool_weight_g));
  const [threshold, setThreshold] = useState(String(row.low_stock_threshold));
  const [target, setTarget] = useState(String(row.target_stock_spools || 0));
  const [location, setLocation] = useState(row.storage_location || "");
  const [notes, setNotes] = useState(row.inventory_notes || "");
  const [movementNote, setMovementNote] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      filament_id: row.filament_id,
      stock_spools: Number(spools),
      opened_remaining_percent: Number(opened),
      spool_weight_g: Number(weight),
      low_stock_threshold: Number(threshold),
      target_stock_spools: Number(target),
      storage_location: location.trim() || null,
      inventory_notes: notes.trim() || null,
      movement_note: movementNote.trim() || null,
    });
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel" role="dialog" aria-modal="true" aria-labelledby="inventory-title">
        <header className="modal-header">
          <div>
            <p className="eyebrow">库存盘点</p>
            <h2 id="inventory-title">{row.brand} · {row.product_line}</h2>
            <p>{row.color || "未记录颜色"}</p>
          </div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭" disabled={busy}>
            <X size={20} />
          </button>
        </header>
        <form onSubmit={submit} className="modal-form">
          <label>
            <span>未开封整卷</span>
            <input min="0" max="10000" step="1" type="number" required value={spools} onChange={(e) => setSpools(e.target.value)} />
          </label>
          <label>
            <span>当前一卷在用余量（%）</span>
            <input min="0" max="100" step="5" type="number" required value={opened} onChange={(e) => setOpened(e.target.value)} />
          </label>
          <div className="opened-spool-actions">
            <button className="secondary-button" type="button" disabled={Number(spools) <= 0 || Number(opened) > 0} onClick={() => { setSpools(String(Math.max(Number(spools) - 1, 0))); setOpened("100"); setMovementNote("开封一卷"); }}>开封一卷</button>
            {[75, 50, 30, 15].map((value) => <button className="quiet-button" type="button" key={value} onClick={() => setOpened(String(value))}>{value}%</button>)}
            <button className="quiet-button" type="button" disabled={Number(opened) === 0} onClick={() => { setOpened("0"); setMovementNote("在用卷已用完"); }}>在用卷用完</button>
          </div>
          <p className="form-hint">当前库存当量约 {(Number(spools || 0) + Number(opened || 0) / 100).toFixed(2)} 卷。网页不再使用 1.3、1.5 这类小数记法。</p>
          <label>
            <span>单卷净重（克）</span>
            <input min="1" max="100000" step="1" type="number" required value={weight} onChange={(e) => setWeight(e.target.value)} />
          </label>
          <label>
            <span>低库存阈值（卷）</span>
            <input min="0" max="10000" step="1" type="number" required value={threshold} onChange={(e) => setThreshold(e.target.value)} />
          </label>
          <label><span>目标库存（卷）</span><input min="0" max="10000" step="1" type="number" required value={target} onChange={(e) => setTarget(e.target.value)} /></label>
          <label><span>存放位置</span><input maxLength={200} value={location} onChange={(e) => setLocation(e.target.value)} placeholder="例如：耗材柜A / 第二层" /></label>
          <label><span>库存备注</span><input maxLength={1000} value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="例如：常用结构件材料" /></label>
          <label><span>本次盘点说明</span><input maxLength={500} value={movementNote} onChange={(e) => setMovementNote(e.target.value)} placeholder="可选，例如：月度盘点修正" /></label>
          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>取消</button>
            <button className="primary-button" type="submit" disabled={busy}>
              <Check size={17} />{busy ? "保存中" : "确认盘点"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}

function ViewNameDialog({ onClose, onSubmit }: { onClose: () => void; onSubmit: (name: string) => void }) {
  const [name, setName] = useState("");
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel compact" role="dialog" aria-modal="true" aria-labelledby="view-title">
        <header className="modal-header">
          <div><p className="eyebrow">当前布局</p><h2 id="view-title">另存为新视图</h2></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭"><X size={20} /></button>
        </header>
        <form className="modal-form" onSubmit={(event) => { event.preventDefault(); if (name.trim()) onSubmit(name.trim()); }}>
          <label><span>视图名称</span><input autoFocus maxLength={30} required value={name} onChange={(e) => setName(e.target.value)} placeholder="例如：常用PETG" /></label>
          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose}>取消</button>
            <button className="primary-button" type="submit" disabled={!name.trim()}><FloppyDisk size={17} />保存视图</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function distinctValues(rows: FilamentRow[], field: keyof FilamentRow, extras: string[] = []): string[] {
  return [...new Set([
    ...extras,
    ...rows.map((row) => row[field]).filter((value): value is string => typeof value === "string" && Boolean(value.trim())),
  ])].sort((left, right) => left.localeCompare(right, "zh-CN"));
}

function SelectOrCustomInput({
  label,
  value,
  options,
  required = false,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  required?: boolean;
  onChange: (value: string) => void;
}) {
  const [customOpen, setCustomOpen] = useState(Boolean(value && !options.includes(value)));
  const customValue = customOpen ? "__custom__" : value;
  const isCustom = customOpen;
  return (
    <label>
      <span>{label}</span>
      <select required={required && !isCustom} value={customValue} onChange={(event) => {
        const next = event.target.value;
        if (next === "__custom__") {
          setCustomOpen(true);
          onChange("");
        } else {
          setCustomOpen(false);
          onChange(next);
        }
      }}>
        <option value="" disabled={required}>{required ? "请选择" : "未设置"}</option>
        {options.map((option) => <option key={option} value={option}>{option}</option>)}
        <option value="__custom__">自定义…</option>
      </select>
      {isCustom && <input autoFocus required={required} maxLength={200} value={value} onChange={(event) => onChange(event.target.value)} placeholder={`输入${label}`} />}
    </label>
  );
}

function FilamentDialog({
  row,
  rows,
  busy,
  onClose,
  onSubmit,
}: {
  row: FilamentRow;
  rows: FilamentRow[];
  busy: boolean;
  onClose: () => void;
  onSubmit: (input: FilamentUpdateInput) => void;
}) {
  const [brand, setBrand] = useState(row.brand || "");
  const [manufacturer, setManufacturer] = useState(row.manufacturer || "");
  const [seller, setSeller] = useState(row.seller || "");
  const [productLine, setProductLine] = useState(row.product_line || "");
  const [material, setMaterial] = useState(row.material_type || "PETG");
  const [variant, setVariant] = useState(row.variant || "");
  const [color, setColor] = useState(row.color || "");
  const [colorFamily, setColorFamily] = useState(row.color_family || "未分类");
  const [diameter, setDiameter] = useState(String(row.diameter_mm || 1.75));
  const [sku, setSku] = useState(row.sku || "");
  const [barcode, setBarcode] = useState(row.barcode || "");
  const [region, setRegion] = useState(row.region || "CN");
  const [status, setStatus] = useState(row.status || "reviewed");
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit({
      filament_id: row.filament_id,
      fields: {
        brand: brand.trim(),
        manufacturer: manufacturer.trim() || null,
        seller: seller.trim() || null,
        product_line: productLine.trim(),
        material_type: material,
        variant: variant.trim() || null,
        color: color.trim() || null,
        color_family: colorFamily || null,
        diameter_mm: Number(diameter),
        sku: sku.trim() || null,
        barcode: barcode.trim() || null,
        region,
        status,
      },
    });
  };

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel wide" role="dialog" aria-modal="true" aria-labelledby="filament-title">
        <header className="modal-header">
          <div><p className="eyebrow">耗材档案</p><h2 id="filament-title">编辑耗材信息</h2><p>库存数量请继续使用独立的“盘点”功能。</p></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭" disabled={busy}><X size={20} /></button>
        </header>
        <form className="modal-form" onSubmit={submit}>
          <div className="filament-form-grid">
            <SelectOrCustomInput label="品牌" required value={brand} onChange={setBrand} options={distinctValues(rows, "brand")} />
            <SelectOrCustomInput label="制造商" value={manufacturer} onChange={setManufacturer} options={distinctValues(rows, "manufacturer")} />
            <SelectOrCustomInput label="销售商" value={seller} onChange={setSeller} options={distinctValues(rows, "seller")} />
            <SelectOrCustomInput label="产品线" required value={productLine} onChange={setProductLine} options={distinctValues(rows, "product_line")} />
            <label><span>材料</span><select required value={material} onChange={(event) => setMaterial(event.target.value)}>{distinctValues(rows, "material_type", MATERIAL_OPTIONS).map((option) => <option key={option} value={option}>{option}</option>)}</select></label>
            <SelectOrCustomInput label="型号/变体" value={variant} onChange={setVariant} options={distinctValues(rows, "variant")} />
            <SelectOrCustomInput label="颜色" value={color} onChange={setColor} options={distinctValues(rows, "color", COMMON_COLORS)} />
            <label><span>色系</span><select value={colorFamily} onChange={(event) => setColorFamily(event.target.value)}>{COLOR_FAMILIES.map((family) => <option key={family}>{family}</option>)}</select></label>
            <label><span>线径</span><select value={diameter} onChange={(event) => setDiameter(event.target.value)}><option value="1.75">1.75 毫米</option><option value="2.85">2.85 毫米</option></select></label>
            <label><span>SKU</span><input maxLength={200} value={sku} onChange={(event) => setSku(event.target.value)} /></label>
            <label><span>条码</span><input maxLength={200} value={barcode} onChange={(event) => setBarcode(event.target.value)} /></label>
            <label><span>地区</span><select value={region} onChange={(event) => setRegion(event.target.value)}>{REGION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}（{value}）</option>)}</select></label>
            <label><span>档案状态</span><select value={status} onChange={(event) => setStatus(event.target.value)}>{STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          </div>
          <p className="form-hint">SKU和条码没有就留空；系统会生成内部标识，不会把它冒充成厂家编号。</p>
          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>取消</button>
            <button className="primary-button" type="submit" disabled={busy}><PencilSimple size={17} />{busy ? "保存中" : "保存档案"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function CreateFilamentDialog({ rows, busy, onClose, onSubmit }: { rows: FilamentRow[]; busy: boolean; onClose: () => void; onSubmit: (input: FilamentCreateInput) => void }) {
  const [brand, setBrand] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [seller, setSeller] = useState("");
  const [productLine, setProductLine] = useState("");
  const [material, setMaterial] = useState("PETG");
  const [variant, setVariant] = useState("");
  const [color, setColor] = useState("");
  const [colorFamily, setColorFamily] = useState("");
  const [diameter, setDiameter] = useState("1.75");
  const [sku, setSku] = useState("");
  const [barcode, setBarcode] = useState("");
  const [region, setRegion] = useState("CN");
  const [stock, setStock] = useState("0");
  const [opened, setOpened] = useState("0");
  const [target, setTarget] = useState("1");
  const [threshold, setThreshold] = useState("1");
  const [weight, setWeight] = useState("1000");
  const [location, setLocation] = useState("");
  return <div className="modal-backdrop"><section className="modal-panel wide" role="dialog" aria-modal="true" aria-labelledby="create-title">
    <header className="modal-header"><div><p className="eyebrow">耗材库</p><h2 id="create-title">新增耗材</h2><p>先记录库存与商品信息，之后可补充商家参数图和客服原话。</p></div><button className="icon-button" type="button" onClick={onClose}><X size={20} /></button></header>
    <form className="modal-form" onSubmit={(event) => { event.preventDefault(); onSubmit({ fields: { brand: brand.trim(), manufacturer: manufacturer.trim() || null, seller: seller.trim() || null, product_line: productLine.trim(), material_type: material, variant: variant.trim() || null, color: color.trim() || null, color_family: colorFamily || null, diameter_mm: Number(diameter), sku: sku.trim() || null, barcode: barcode.trim() || null, region, status: "reviewed" }, stock_spools: Number(stock), opened_remaining_percent: Number(opened), spool_weight_g: Number(weight), low_stock_threshold: Number(threshold), target_stock_spools: Number(target), storage_location: location.trim() || null, inventory_notes: null }); }}>
      <div className="filament-form-grid">
        <SelectOrCustomInput label="品牌" required value={brand} onChange={setBrand} options={distinctValues(rows, "brand")} />
        <SelectOrCustomInput label="制造商" value={manufacturer} onChange={setManufacturer} options={distinctValues(rows, "manufacturer")} />
        <SelectOrCustomInput label="销售商" value={seller} onChange={setSeller} options={distinctValues(rows, "seller")} />
        <SelectOrCustomInput label="产品线" required value={productLine} onChange={setProductLine} options={distinctValues(rows, "product_line")} />
        <label><span>材料</span><select value={material} onChange={(e) => setMaterial(e.target.value)}>{MATERIAL_OPTIONS.map((item) => <option key={item}>{item}</option>)}</select></label>
        <SelectOrCustomInput label="型号/变体" value={variant} onChange={setVariant} options={distinctValues(rows, "variant")} />
        <SelectOrCustomInput label="颜色" value={color} onChange={setColor} options={distinctValues(rows, "color", COMMON_COLORS)} />
        <label><span>色系</span><select value={colorFamily} onChange={(event) => setColorFamily(event.target.value)}><option value="">自动分类</option>{COLOR_FAMILIES.map((family) => <option key={family}>{family}</option>)}</select></label>
        <label><span>线径</span><select value={diameter} onChange={(e) => setDiameter(e.target.value)}><option value="1.75">1.75 毫米</option><option value="2.85">2.85 毫米</option></select></label>
        <label><span>SKU</span><input maxLength={200} value={sku} onChange={(e) => setSku(e.target.value)} /></label>
        <label><span>条码</span><input maxLength={200} value={barcode} onChange={(e) => setBarcode(e.target.value)} /></label>
        <label><span>地区</span><select value={region} onChange={(e) => setRegion(e.target.value)}>{REGION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}（{value}）</option>)}</select></label>
        <label><span>未开封整卷</span><input type="number" min="0" max="10000" required value={stock} onChange={(e) => setStock(e.target.value)} /></label>
        <label><span>一卷在用余量（%）</span><input type="number" min="0" max="100" step="5" required value={opened} onChange={(e) => setOpened(e.target.value)} /></label>
        <label><span>目标库存（卷）</span><input type="number" min="0" max="10000" required value={target} onChange={(e) => setTarget(e.target.value)} /></label>
        <label><span>低库存阈值（卷）</span><input type="number" min="0" max="10000" required value={threshold} onChange={(e) => setThreshold(e.target.value)} /></label>
        <label><span>单卷净重（克）</span><input type="number" min="1" max="100000" required value={weight} onChange={(e) => setWeight(e.target.value)} /></label>
        <label><span>存放位置</span><input maxLength={200} value={location} onChange={(e) => setLocation(e.target.value)} /></label>
      </div>
      <p className="form-hint">没有SKU或条码也可以先建档；系统会生成内部标识，之后可在编辑页补充真实编号。</p>
      <div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose}>取消</button><button className="primary-button" type="submit" disabled={busy}><Plus size={17} />{busy ? "创建中" : "创建耗材"}</button></div>
    </form>
  </section></div>;
}

function DetailDialog({ detail, busy, onClose, onUndo }: { detail: FilamentDetail; busy: boolean; onClose: () => void; onUndo: (id: string) => void }) {
  const row = detail.filament;
  const reversed = new Set(detail.movements.filter((item) => item.reverses_movement_id).map((item) => item.reverses_movement_id));
  const undoableMovementId = detail.movements[0]?.movement_type !== "undo" ? detail.movements[0]?.id : null;
  const valueText = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value, null, 0);
  return <div className="modal-backdrop"><section className="modal-panel detail-panel" role="dialog" aria-modal="true" aria-labelledby="detail-title">
    <header className="modal-header"><div><p className="eyebrow">耗材详情</p><h2 id="detail-title">{row.brand} · {row.product_line}</h2><p>{row.material_type} · {row.color || "未记录颜色"} · {row.readiness_label}</p></div><button className="icon-button" type="button" onClick={onClose}><X size={20} /></button></header>
    <div className="detail-content">
      <section className="detail-grid"><div><span>当前库存</span><strong>{row.stock_spools} 卷</strong></div><div><span>目标库存</span><strong>{row.target_stock_spools} 卷</strong></div><div><span>建议补货</span><strong>{row.replenishment_spools} 卷</strong></div><div><span>存放位置</span><strong>{row.storage_location || "未设置"}</strong></div></section>
      <section className="detail-section"><h3>打印准备状态</h3><div className="readiness-line"><span className={`readiness-badge readiness-${row.readiness_state}`}>{row.readiness_label}</span><span>{row.profile_count} 个预设 · {row.calibration_count} 次校准 · {row.conflict_count} 个冲突字段</span></div></section>
      <section className="detail-section"><h3>预设</h3>{detail.profiles.length ? <div className="record-list">{detail.profiles.map((item, index) => <div key={String(item.id || index)}><strong>{String(item.baseline_name || "未命名预设")}</strong><span>{String(item.target_printer || "")}, {String(item.nozzle_mm || "")} mm</span><small>{String(item.status || "")}</small></div>)}</div> : <p className="empty-note">尚无预设记录。</p>}</section>
      <section className="detail-section"><h3>个人校准</h3>{detail.calibrations.length ? <div className="record-list">{detail.calibrations.map((item, index) => <div key={String(item.id || index)}><strong>{String(item.test_type || "校准")}</strong><span>{String(item.machine || "")} · {String(item.nozzle_mm || "")} mm</span><small>{String(item.status || "")}</small></div>)}</div> : <p className="empty-note">尚无校准记录。</p>}</section>
      <section className="detail-section"><h3>厂家事实与冲突</h3>{detail.claims.length ? <div className="claim-table">{detail.claims.map((item, index) => <div key={String(item.id || index)}><strong>{String(item.claim_key || "参数")}</strong><code>{valueText(item.value)} {String(item.unit || "")}</code><span>{String(item.authority || "unknown")} · {String(item.review_status || "pending")}</span></div>)}</div> : <p className="empty-note">尚无厂家事实记录。</p>}</section>
      <section className="detail-section"><h3>库存操作历史</h3>{detail.movements.length ? <div className="movement-list">{detail.movements.map((item) => <div key={item.id}><span className={item.delta > 0 ? "positive" : "negative"}>{item.delta > 0 ? "+" : ""}{item.delta}</span><div><strong>{({purchase:"购买入库",usage:"打印消耗",count:"盘点修正",correction:"库存修正",undo:"撤销"} as Record<string,string>)[item.movement_type]}</strong><small>{item.note || `${item.before_spools} → ${item.after_spools} 卷`}</small></div>{item.id === undoableMovementId && !reversed.has(item.id) && <button className="secondary-button" type="button" disabled={busy} onClick={() => onUndo(item.id)}><ArrowCounterClockwise size={15} />撤销</button>}</div>)}</div> : <p className="empty-note">尚无库存操作记录。</p>}</section>
    </div>
  </section></div>;
}

function DetailPage({ detail, busy, onBack, onEdit, onCount, onAddEvidence, onUndo }: { detail: FilamentDetail; busy: boolean; onBack: () => void; onEdit: () => void; onCount: () => void; onAddEvidence: () => void; onUndo: (id: string) => void }) {
  const row = detail.filament;
  const reversed = new Set(detail.movements.filter((item) => item.reverses_movement_id).map((item) => item.reverses_movement_id));
  const undoableMovementId = detail.movements[0]?.movement_type !== "undo" ? detail.movements[0]?.id : null;
  const badgeVariant = row.conflict_count > 0 ? "destructive" : row.source_count > 0 ? "default" : "secondary";
  const valueText = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value);
  return <section className="detail-page">
    <div className="detail-page-header">
      <div><Button variant="ghost" size="sm" onClick={onBack}>← 返回耗材库</Button><div className="detail-title-row"><div className="material-swatch size-12" style={{ backgroundColor: colorPreview(row.color) }} /><div><p className="eyebrow">{row.material_type} · {row.color || "未记录颜色"}</p><h1>{row.brand} · {row.product_line}</h1><p>{row.sku || row.barcode || "未记录产品标识"}</p></div></div></div>
      <div className="heading-actions"><Button variant="outline" onClick={onAddEvidence}><Plus />添加厂家资料</Button><Button variant="outline" onClick={onEdit}><PencilSimple />编辑档案</Button><Button onClick={onCount}><Scales />库存盘点</Button></div>
    </div>
    <div className="detail-kpi-grid">
      <Card><CardHeader><CardDescription>未开封整卷</CardDescription><CardTitle className="text-2xl">{row.stock_spools} 卷</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>当前在用卷</CardDescription><CardTitle className="text-2xl">{row.opened_remaining_percent ? `${row.opened_remaining_percent}%` : "无"}</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>库存当量</CardDescription><CardTitle className="text-2xl">{row.stock_equivalent} 卷</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>建议补货</CardDescription><CardTitle className="text-2xl">{row.replenishment_spools} 卷</CardTitle></CardHeader></Card>
    </div>
    <div className="detail-columns">
      <div className="detail-primary-column">
        <Card><CardHeader><div className="card-heading-row"><div><CardTitle>档案完整性</CardTitle><CardDescription>只检查库存、商家资料、颜色归类和冲突项。</CardDescription></div><Badge variant={badgeVariant}>{row.source_count > 0 ? "已有商家资料" : "待补资料"}</Badge></div></CardHeader><CardContent><div className="readiness-metrics"><span>{row.source_count}<small>原始资料</small></span><span>{row.claim_count}<small>参数声明</small></span><span>{row.conflict_count}<small>冲突项</small></span></div><p className="next-action"><strong>下一步</strong>{nextActionFor(row)}</p></CardContent></Card>
        <Card><CardHeader><CardTitle>厂家事实与冲突</CardTitle><CardDescription>厂家声明与个人数据分开保存；冲突不会被静默覆盖。</CardDescription></CardHeader><CardContent>{detail.claims.length ? <div className="claim-table">{detail.claims.map((item, index) => <div key={String(item.id || index)}><strong>{claimKeyLabel(String(item.claim_key || "参数"))}</strong><code>{valueText(item.value)} {String(item.unit || "")}</code><span>{String(item.authority || "unknown")} · {String(item.review_status || "pending")}</span></div>)}</div> : <p className="empty-note">尚无厂家事实记录。</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>资料来源</CardTitle><CardDescription>截图、PDF、销售页和客服原话都保留原始证据；点击文件可查看。</CardDescription></CardHeader><CardContent>{detail.sources.length ? <div className="record-list evidence-list">{detail.sources.map((source) => <div key={source.id}><div><strong>{source.title || "未命名资料"}</strong><span>{sourceKindLabel(source.kind)}{source.source_organization ? ` · ${source.source_organization}` : ""}</span><small>{sourceDecisionLabel(String(source.metadata?.user_decision || "undecided"))}{source.region ? ` · ${source.region}` : ""}{source.origin ? ` · ${source.origin}` : ""}</small></div><a className="secondary-button" href={source.file_url} target="_blank" rel="noreferrer">查看原件</a></div>)}</div> : <p className="empty-note">尚未上传厂家或客服资料。</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>库存操作历史</CardTitle><CardDescription>只允许撤销最新一项库存操作，避免历史数量链断裂。</CardDescription></CardHeader><CardContent>{detail.movements.length ? <div className="movement-list">{detail.movements.map((item) => <div key={item.id}><span className={item.delta > 0 ? "positive" : "negative"}>{item.delta > 0 ? "+" : ""}{item.delta}</span><div><strong>{({purchase:"购买入库",usage:"打印消耗",count:"盘点修正",correction:"库存修正",undo:"撤销"} as Record<string,string>)[item.movement_type]}</strong><small>{item.note || `${item.before_spools} → ${item.after_spools} 卷`}</small></div>{item.id === undoableMovementId && !reversed.has(item.id) && <Button variant="outline" size="sm" disabled={busy} onClick={() => onUndo(item.id)}><ArrowCounterClockwise />撤销</Button>}</div>)}</div> : <p className="empty-note">尚无库存操作记录。</p>}</CardContent></Card>
      </div>
      <aside className="detail-secondary-column">
        <Card><CardHeader><CardTitle>产品信息</CardTitle><CardDescription>库存矩阵中的原始维度</CardDescription></CardHeader><CardContent><div className="record-list"><div><strong>商家颜色名</strong><span>{row.color || "未记录"}</span></div><div><strong>标准色系</strong><span>{row.color_family}</span></div><div><strong>存放位置</strong><span>{row.storage_location || "未设置"}</span></div><div><strong>型号 / 变体</strong><span>{row.variant || "未记录"}</span></div></div></CardContent></Card>
        {(detail.profiles.length > 0 || detail.calibrations.length > 0) && <Card><CardHeader><CardTitle>已有工艺记录</CardTitle><CardDescription>只展示历史数据，本页面不会自动生成方案。</CardDescription></CardHeader><CardContent><p className="empty-note">{detail.profiles.length} 个预设 · {detail.calibrations.length} 次校准</p></CardContent></Card>}
      </aside>
    </div>
  </section>;
}

function authorityLabel(authority: string): string {
  return ({ bambu_system: "拓竹系统预设", manufacturer_profile: "厂家提供预设", user_profile: "用户预设 / 待核验" } as Record<string, string>)[authority] || authority;
}

function ProductDetailPage({ detail, busy, onBack, onOpenColor, onCount, onAddPreset, onAddEvidence }: { detail: ProductDetail; busy: boolean; onBack: () => void; onOpenColor: (id: string) => void; onCount: (row: FilamentRow) => void; onAddPreset: () => void; onAddEvidence: () => void }) {
  const product = detail.product;
  const catalogClaims = detail.product_claims.filter((item) => item.claim_key === "available_colors");
  const productClaims = detail.product_claims.filter((item) => item.claim_key !== "available_colors");
  const presetComparisons = compareClaimsToPresets(productClaims, detail.presets);
  return <section className="detail-page product-detail-page">
    <div className="detail-page-header">
      <div><Button variant="ghost" size="sm" onClick={onBack}>← 返回产品目录</Button><div className="detail-title-row"><div className="brand-mark">{product.brand.slice(0, 2).toUpperCase()}</div><div><p className="eyebrow">{product.material_type}{product.formulation ? ` · ${product.formulation}` : ""}</p><h1>{product.brand} · {product.product_line}</h1><p>{product.diameter_mm} mm · {product.region} · {detail.summary.color_count} 个颜色库存项</p></div></div></div>
      <div className="heading-actions"><Button onClick={onAddEvidence}><Plus />上传资料截图</Button><Button variant="outline" onClick={onAddPreset}><Plus />添加厂家预设</Button></div>
    </div>
    <div className="detail-kpi-grid">
      <Card><CardHeader><CardDescription>颜色规格</CardDescription><CardTitle className="text-2xl">{detail.summary.color_count} 种</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>库存当量</CardDescription><CardTitle className="text-2xl">{detail.summary.stock_equivalent} 卷</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>厂家声明</CardDescription><CardTitle className="text-2xl">{detail.summary.product_claim_count} 项</CardTitle></CardHeader></Card>
      <Card><CardHeader><CardDescription>预设评测</CardDescription><CardTitle className="text-2xl">{detail.summary.preset_count} 份</CardTitle></CardHeader></Card>
    </div>
    <div className="detail-columns">
      <div className="detail-primary-column">
        {catalogClaims.length > 0 && <Card><CardHeader><CardTitle>系列颜色目录</CardTitle><CardDescription>这里维护厂家/商家为该系列提供的颜色名称，不代表已经入库。</CardDescription></CardHeader><CardContent><div className="series-color-catalog">{catalogClaims.map((claim) => <div key={claim.id}><div className="color-chip-list">{claimColors(claim.value).map((color) => <span key={color}><i style={{ backgroundColor: colorPreview(color) }} />{color}</span>)}</div><small>{claim.source?.source_organization || claim.authority || "来源待核验"} · {claim.review_status}</small></div>)}</div></CardContent></Card>}
        <Card><CardHeader><CardTitle>当前在库颜色</CardTitle><CardDescription>库存数量和颜色实测在这一层；系列目录中的其他颜色不会制造库存。</CardDescription></CardHeader><CardContent><div className="product-color-list">{detail.colors.map((row) => <div key={row.filament_id}><button className="color-main" type="button" onClick={() => onOpenColor(row.filament_id)}><span className="material-swatch" style={{backgroundColor: colorPreview(row.color)}} /><span><strong>{row.color || "未记录颜色"}</strong><small>{row.color_family} · {row.sku || "无SKU"}</small></span></button><span className="color-stock"><strong>{row.stock_equivalent}</strong><small>卷当量</small></span><Button variant="outline" size="sm" disabled={busy} onClick={() => onCount(row)}>盘点</Button></div>)}</div></CardContent></Card>
        <Card><CardHeader><CardTitle>厂家产品参数</CardTitle><CardDescription>打印参数、物理性能和机械性能都保留；无法归类的字段使用原名称保存。</CardDescription></CardHeader><CardContent>{productClaims.length ? <div className="claim-table">{productClaims.map((item) => <div key={item.id}><strong>{claimKeyLabel(item.claim_key)}</strong><code>{claimValueText(item.value)} {item.unit || ""}</code><span>{item.authority || "unknown"} · {item.review_status}</span></div>)}</div> : <p className="empty-note">尚无产品级厂家参数。</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>厂家预设与评测</CardTitle><CardDescription>预设是可追溯的参数证据；透明/白色存在差异时单独绑定颜色。</CardDescription></CardHeader><CardContent>{detail.presets.length ? <div className="preset-list">{detail.presets.map((preset) => <div key={preset.id}><div><strong>{preset.profile_name}</strong><span>{preset.target_printer} · {preset.nozzle_mm} mm</span><small>{authorityLabel(preset.authority)} · {preset.scope_level === "product" ? "产品通用" : `颜色专用：${detail.colors.find((row) => row.filament_id === preset.filament_id)?.color || "未命名"}`}</small><small>{preset.provenance}{preset.internal_origin ? ` · 文件内部来源 ${preset.internal_origin}` : ""}</small>{preset.warnings?.map((warning) => <small className="preset-warning" key={warning}>{warning}</small>)}</div><Badge variant={preset.review_status === "approved" ? "default" : "secondary"}>{preset.review_status === "approved" ? "已审核" : "待审核"}</Badge></div>)}</div> : <p className="empty-note">尚无预设评测记录。</p>}</CardContent></Card>
        {presetComparisons.length > 0 && <Card><CardHeader><CardTitle>厂家资料与预设对比</CardTitle><CardDescription>只比较语义相同的温度、风扇和密度；不会拿“最高速度”推算最大体积流量。</CardDescription></CardHeader><CardContent><div className="preset-comparison-list">{presetComparisons.map((item) => <div key={item.id}><Badge variant={item.conflict ? "destructive" : "default"}>{item.conflict ? "冲突" : "相容"}</Badge><div><strong>{item.label}</strong><span>厂家：{item.claimValue}</span><small>{item.presetName}：{item.presetValue}</small></div></div>)}</div></CardContent></Card>}
      </div>
      <aside className="detail-secondary-column">
        <Card><CardHeader><CardTitle>产品身份</CardTitle><CardDescription>配方/工艺型号与颜色分离</CardDescription></CardHeader><CardContent><div className="record-list"><div><strong>品牌</strong><span>{product.brand}</span></div><div><strong>制造商</strong><span>{product.manufacturer || "未记录"}</span></div><div><strong>产品线</strong><span>{product.product_line}</span></div><div><strong>配方 / 表面</strong><span>{product.formulation || "常规"}</span></div></div></CardContent></Card>
        <Card><CardHeader><CardTitle>资料收件箱</CardTitle><CardDescription>原图先私有留存；你指定后由我批量整理并关联结构化事实。</CardDescription></CardHeader><CardContent>{detail.sources.length ? <div className="evidence-inbox-list">{detail.sources.map((source) => <div key={source.id}>{source.media_type?.startsWith("image/") && <a className="evidence-preview" href={source.file_url} target="_blank" rel="noreferrer"><img src={source.file_url} alt={source.title || "资料截图"} loading="lazy" /></a>}<div><strong>{source.title || "未命名资料"}</strong><span>{source.source_organization || source.kind} · {source.scope_level === "color_variant" ? "颜色专用" : "产品通用"}</span></div>{source.metadata?.processing_status === "pending_manual_review" ? <Badge variant="secondary">待整理</Badge> : source.metadata?.processing_status === "processed" ? <Badge variant="default">已整理</Badge> : null}<a href={source.file_url} target="_blank" rel="noreferrer">查看原件</a></div>)}</div> : <p className="empty-note">尚未上传资料。</p>}</CardContent></Card>
        <Card><CardHeader><CardTitle>颜色级记录</CardTitle><CardDescription>温度塔、流量、K/PA及颜色专用预设不污染产品事实。</CardDescription></CardHeader><CardContent><div className="readiness-metrics"><span>{detail.summary.color_claim_count}<small>颜色声明</small></span><span>{detail.presets.filter((item) => item.scope_level === "color_variant").length}<small>颜色预设</small></span></div></CardContent></Card>
      </aside>
    </div>
  </section>;
}

function ProductEvidenceDialog({ detail, busy, onClose, onSubmit }: { detail: ProductDetail; busy: boolean; onClose: () => void; onSubmit: (source: ProductEvidenceCreateInput["source"], files: File[]) => Promise<unknown> | void }) {
  const product = detail.product;
  const [kind, setKind] = useState<ProductEvidenceCreateInput["source"]["kind"]>("seller");
  const [organization, setOrganization] = useState(product.seller || product.manufacturer || product.brand);
  const [region, setRegion] = useState(product.region || "CN");
  const [title, setTitle] = useState("");
  const [origin, setOrigin] = useState("");
  const [notes, setNotes] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!files.length) { setError("请选择至少一张资料图片。"); return; }
    await onSubmit({ kind, title: title.trim() || null, source_organization: organization.trim() || null, region, origin: origin.trim() || null, notes: notes.trim() || null }, files);
  };
  return <div className="modal-backdrop"><section className="modal-panel wide" role="dialog" aria-modal="true" aria-labelledby="product-evidence-title">
    <header className="modal-header"><div><p className="eyebrow">资料收件箱</p><h2 id="product-evidence-title">上传产品截图</h2><p>{product.brand} · {product.product_line}</p></div><button className="icon-button" type="button" onClick={onClose} disabled={busy}><X size={20} /></button></header>
    <form className="modal-form" onSubmit={(event) => void submit(event)}>
      <div className="form-note">这里先保存商家页面、厂家参数表或客服截图的原图；你指定后由我批量整理，不在上传时阻塞等待识图。</div>
      <div className="form-grid">
        <label><span>资料来源</span><select value={kind} onChange={(event) => setKind(event.target.value as ProductEvidenceCreateInput["source"]["kind"])}><option value="seller">销售商 / 商品页</option><option value="manufacturer">制造商 / 厂家</option><option value="customer_service">客服回复</option><option value="user_note">个人补充</option></select></label>
        <label><span>来源单位</span><input maxLength={200} value={organization} onChange={(event) => setOrganization(event.target.value)} placeholder="厂家、店铺或客服名称" /></label>
        <label><span>资料地区</span><select value={region} onChange={(event) => setRegion(event.target.value)}>{REGION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}（{value}）</option>)}</select></label>
        <label><span>资料标题（可选）</span><input maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="留空则使用图片文件名" /></label>
        <label className="form-span-2"><span>原始链接（可选）</span><input maxLength={1000} value={origin} onChange={(event) => setOrigin(event.target.value)} placeholder="商品页或厂家页面地址" /></label>
        <label className="form-span-2"><span>备注（可选）</span><textarea maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="例如：客服于2026-08-14发送；参数适用于整个产品" /></label>
        <label className="form-span-2 upload-dropzone"><strong>{files.length ? `已选择 ${files.length} 张图片` : "选择资料截图"}</strong><span>PNG、JPG、WebP；最多10张，单张不超过8MB</span><input multiple type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => { const next = Array.from(event.target.files || []); const invalid = next.find((file) => !["image/png", "image/jpeg", "image/webp"].includes(file.type) || file.size === 0 || file.size > 8 * 1024 * 1024); if (next.length > 10) { setFiles([]); setError("一次最多上传10张图片。"); } else if (invalid) { setFiles([]); setError(`${invalid.name} 不是有效图片或超过8MB。`); } else { setFiles(next); setError(null); } }} /></label>
        {files.length > 0 && <div className="form-span-2 upload-file-list">{files.map((file) => <span key={`${file.name}-${file.lastModified}`}>{file.name}<small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></span>)}</div>}
        {error && <small className="form-span-2 field-error">{error}</small>}
      </div>
      <footer className="modal-actions"><Button type="button" variant="outline" onClick={onClose} disabled={busy}>取消</Button><Button type="submit" disabled={busy}>{busy ? "正在保存…" : `保存${files.length || ""}张原图`}</Button></footer>
    </form>
  </section></div>;
}

function ProductPresetDialog({ detail, busy, onClose, onSubmit }: { detail: ProductDetail; busy: boolean; onClose: () => void; onSubmit: (input: ProductPresetCreateInput) => Promise<unknown> | void }) {
  const [authority, setAuthority] = useState<ProductPresetCreateInput["authority"]>("manufacturer_profile");
  const [provenance, setProvenance] = useState("厂家提供，用户转存");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file) { setError("请选择JSON或BBSFLMT预设文件。"); return; }
    await onSubmit({
      product_id: detail.product.id,
      filament_id: null,
      authority,
      provenance: provenance.trim(),
      file: { filename: file.name, data_base64: await fileToBase64(file) },
    });
  };
  return <div className="modal-backdrop"><section className="modal-panel wide" role="dialog" aria-modal="true" aria-labelledby="preset-title">
    <header className="modal-header"><div><p className="eyebrow">厂家参数证据</p><h2 id="preset-title">添加耗材预设</h2><p>{detail.product.brand} · {detail.product.product_line}</p></div><button className="icon-button" type="button" onClick={onClose} disabled={busy}><X size={20} /></button></header>
    <form className="modal-form" onSubmit={(event) => void submit(event)}>
      <div className="form-grid">
        <label><span>来源身份</span><select value={authority} onChange={(event) => setAuthority(event.target.value as ProductPresetCreateInput["authority"])}><option value="manufacturer_profile">厂家提供预设</option><option value="bambu_system">拓竹系统预设</option><option value="user_profile">用户预设 / 待核验</option></select></label>
        <label className="form-span-2"><span>来源链说明</span><input required maxLength={1000} value={provenance} onChange={(event) => setProvenance(event.target.value)} placeholder="例如：厂家客服发送，用户从Bambu Studio导出" /></label>
        <label className="form-span-2"><span>JSON / BBSFLMT 文件</span><input required type="file" accept=".json,.bbsflmt" onChange={(event) => { const next = event.target.files?.[0] || null; if (next && next.size > 8 * 1024 * 1024) { setFile(null); setError("文件不能超过8MB。"); } else { setFile(next); setError(null); } }} />{error && <small className="field-error">{error}</small>}</label>
      </div>
      <div className="form-note">系统只提取 A1 0.4 mm 的白名单字段，并自动判断产品通用或白色/透明等颜色专用预设。文件内部的 <code>from=User</code> 会保留，不会冒充拓竹系统预设。低温板为 0 时会额外标记 Glacier 评估警告。</div>
      <footer className="modal-actions"><Button type="button" variant="outline" onClick={onClose} disabled={busy}>取消</Button><Button type="submit" disabled={busy}>{busy ? "正在解析…" : "解析并建档"}</Button></footer>
    </form>
  </section></div>;
}

function ProductCatalog({ products, search, onOpen }: { products: ProductSummary[]; search: string; onOpen: (id: string) => void }) {
  const needle = search.trim().toLocaleLowerCase("zh-CN");
  const rows = products.filter((product) => !needle || [product.brand, product.product_line, product.material_type, product.formulation, ...product.colors.map((row) => row.color)].filter(Boolean).some((value) => String(value).toLocaleLowerCase("zh-CN").includes(needle)));
  return <div className="product-catalog-grid">{rows.map((product) => <article className="product-catalog-card" key={product.product_id}><header><div><p className="eyebrow">{product.material_type}{product.formulation ? ` · ${product.formulation}` : ""}</p><h3>{product.brand} · {product.product_line}</h3></div><Badge variant={product.manufacturer_preset_count ? "default" : "secondary"}>{product.manufacturer_preset_count ? "有厂家预设" : "待补预设"}</Badge></header><div className="product-color-chips">{product.colors.slice(0, 12).map((row) => <span key={row.filament_id} title={`${row.color || "未命名"} · ${row.stock_equivalent}卷`}><i style={{backgroundColor: colorPreview(row.color)}} />{row.color || "未命名"}</span>)}{product.colors.length > 12 && <span>+{product.colors.length - 12}</span>}</div><dl><div><dt>颜色</dt><dd>{product.color_count} 种</dd></div><div><dt>库存当量</dt><dd>{product.stock_equivalent} 卷</dd></div><div><dt>厂家资料</dt><dd>{product.source_count} 份</dd></div><div><dt>预设评测</dt><dd>{product.preset_count} 份</dd></div></dl><Button onClick={() => onOpen(product.product_id)}>查看产品</Button></article>)}{rows.length === 0 && <div className="empty-state"><Package size={28} /><h3>没有匹配产品</h3><p>请调整搜索条件。</p></div>}</div>;
}

async function fileToBase64(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  let binary = "";
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, Math.min(index + chunkSize, bytes.length)));
  }
  return btoa(binary);
}

async function normalizedImageBase64(file: File): Promise<string> {
  const bitmap = await createImageBitmap(file);
  try {
    const scale = Math.min(1, 2200 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    const context = canvas.getContext("2d");
    if (!context) throw new Error("浏览器无法处理这张图片。");
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise<Blob>((resolve, reject) =>
      canvas.toBlob((value) => value ? resolve(value) : reject(new Error("图片转换失败。")), "image/png"),
    );
    return fileToBase64(new File([blob], "recognition.png", { type: "image/png" }));
  } finally {
    bitmap.close();
  }
}

function EvidenceDialog({ detail, busy, onClose, onSubmit }: { detail: FilamentDetail; busy: boolean; onClose: () => void; onSubmit: (input: EvidenceCreateInput) => Promise<unknown> | void }) {
  const row = detail.filament;
  const [kind, setKind] = useState<EvidenceCreateInput["source"]["kind"]>("seller");
  const [scopeLevel, setScopeLevel] = useState<EvidenceCreateInput["source"]["scope_level"]>("product");
  const [title, setTitle] = useState(`${row.brand || "耗材"} 参数资料`);
  const [organization, setOrganization] = useState(row.seller || row.manufacturer || "");
  const [origin, setOrigin] = useState("");
  const [sourceRegion, setSourceRegion] = useState(row.region || "CN");
  const [documentVersion, setDocumentVersion] = useState("");
  const [decision, setDecision] = useState<EvidenceCreateInput["source"]["user_decision"]>("undecided");
  const [quote, setQuote] = useState("");
  const [notes, setNotes] = useState("");
  const [claims, setClaims] = useState<Array<{ key: string; value: string; unit: string }>>([
    { key: "nozzle_temperature", value: "", unit: "°C" },
  ]);
  const [file, setFile] = useState<File | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [readingFile, setReadingFile] = useState(false);

  const updateClaim = (index: number, field: "key" | "value" | "unit", value: string) => {
    setClaims((current) => current.map((claim, claimIndex) => claimIndex === index ? { ...claim, [field]: value } : claim));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setReadingFile(true);
    try {
      const filteredClaims = claims
        .filter((claim) => claim.value.trim())
        .map((claim) => ({ key: claim.key, value: claim.value.trim(), unit: claim.unit.trim() || null }));
      const input: EvidenceCreateInput = {
        filament_id: row.filament_id,
        source: {
          scope_level: scopeLevel,
          kind,
          title: title.trim(),
          source_organization: organization.trim() || null,
          origin: origin.trim() || null,
          region: sourceRegion.trim() || null,
          document_version: documentVersion.trim() || null,
          user_decision: decision,
          quote: quote.trim() || null,
          notes: notes.trim() || null,
        },
        claims: filteredClaims,
      };
      if (file) {
        input.file = { filename: file.name, media_type: file.type || "application/octet-stream", data_base64: await fileToBase64(file) };
      }
      await onSubmit(input);
    } finally {
      setReadingFile(false);
    }
  };

  return <div className="modal-backdrop" role="presentation"><section className="modal-panel wide" role="dialog" aria-modal="true" aria-labelledby="evidence-title">
    <header className="modal-header"><div><p className="eyebrow">耗材资料</p><h2 id="evidence-title">添加厂家 / 商家资料</h2><p>原话不会自动改写成温度或速度；结构化参数用于后续横向比较。</p></div><button className="icon-button" type="button" onClick={onClose} aria-label="关闭" disabled={busy || readingFile}><X size={20} /></button></header>
    <form className="modal-form" onSubmit={(event) => void submit(event)}>
      <div className="filament-form-grid">
        <label><span>适用范围</span><select value={scopeLevel} onChange={(event) => setScopeLevel(event.target.value as EvidenceCreateInput["source"]["scope_level"])}><option value="product">整个产品（厂家通用资料）</option><option value="color_variant">当前颜色（温度塔/流量/颜色反馈）</option></select></label>
        <label><span>资料类型</span><select value={kind} onChange={(event) => setKind(event.target.value as EvidenceCreateInput["source"]["kind"])}>{SOURCE_KIND_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span>资料标题</span><input required maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：遇果常规PETG黑色客服回复" /></label>
        <label><span>商家/厂家</span><input maxLength={200} value={organization} onChange={(event) => setOrganization(event.target.value)} placeholder="例如：遇果" /></label>
        <label><span>来源链接或渠道</span><input maxLength={1000} value={origin} onChange={(event) => setOrigin(event.target.value)} placeholder="商品页、客服渠道或订单备注" /></label>
        <label><span>资料地区</span><select value={sourceRegion} onChange={(event) => setSourceRegion(event.target.value)}>{REGION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}（{value}）</option>)}</select></label>
        <label><span>资料版本/批次（可选）</span><input maxLength={100} value={documentVersion} onChange={(event) => setDocumentVersion(event.target.value)} placeholder="例如：2026-08 页面版本" /></label>
        <label><span>采用决定</span><select value={decision} onChange={(event) => setDecision(event.target.value as EvidenceCreateInput["source"]["user_decision"])}>{SOURCE_DECISION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
        <label><span>原始文件（可选，最大8MB）</span><input type="file" accept=".png,.jpg,.jpeg,.webp,.pdf,.json,.bbsflmt,.txt" onChange={(event) => { const selected = event.target.files?.[0] || null; if (selected && selected.size > 8 * 1024 * 1024) { setFile(null); setFileError("文件超过8MB，请压缩后再上传。"); } else { setFile(selected); setFileError(null); } }} />{fileError && <small className="field-error">{fileError}</small>}</label>
      </div>
      <div className="form-note">产品级资料只保存一次并由所有颜色继承；当前颜色资料仅用于这一颜色的温度塔、流量、K/PA或实际反馈。</div>
      <label><span>商家 / 客服原话</span><textarea maxLength={4000} value={quote} onChange={(event) => setQuote(event.target.value)} placeholder="例如：按照默认参数打就行" /></label>
      <div className="evidence-claims-editor"><div className="section-heading"><div><strong>结构化参数（可选）</strong><small>可从建议字段选择，也可直接输入新的字段标识；未知信息不会丢弃。</small></div><button className="secondary-button" type="button" onClick={() => setClaims((current) => [...current, { key: "source_note", value: "", unit: "" }])}><Plus size={15} />添加参数</button></div>{claims.map((claim, index) => <div className="evidence-claim-row" key={`${index}-${claim.key}`}><input list="claim-key-options" maxLength={100} value={claim.key} onChange={(event) => updateClaim(index, "key", event.target.value)} placeholder="字段标识" /><input required={false} placeholder="数值或原文" value={claim.value} onChange={(event) => updateClaim(index, "value", event.target.value)} /><input maxLength={50} placeholder="单位" value={claim.unit} onChange={(event) => updateClaim(index, "unit", event.target.value)} />{claims.length > 1 && <button className="icon-button" type="button" aria-label="删除参数" onClick={() => setClaims((current) => current.filter((_, claimIndex) => claimIndex !== index))}><Trash size={16} /></button>}</div>)}<datalist id="claim-key-options">{CLAIM_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</datalist></div>
      <label><span>备注</span><textarea maxLength={2000} value={notes} onChange={(event) => setNotes(event.target.value)} placeholder="例如：客服确认可直接套用默认参数" /></label>
      <div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose} disabled={busy || readingFile}>取消</button><button className="primary-button" type="submit" disabled={busy || readingFile || Boolean(fileError) || !title.trim()}><Check size={17} />{readingFile ? "读取文件中" : busy ? "保存中" : "保存资料"}</button></div>
    </form>
  </section></div>;
}

type SmartImportSubmission = {
  filament: FilamentCreateInput;
  evidence: Omit<EvidenceCreateInput, "filament_id">;
};

function SmartImportDialog({ rows, busy, onClose, onSubmit }: { rows: FilamentRow[]; busy: boolean; onClose: () => void; onSubmit: (input: SmartImportSubmission) => Promise<unknown> | void }) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImageRecognitionResult | null>(null);
  const [recognizing, setRecognizing] = useState(false);
  const [recognitionError, setRecognitionError] = useState<string | null>(null);
  const [brand, setBrand] = useState("待识别品牌");
  const [seller, setSeller] = useState("");
  const [productLine, setProductLine] = useState("待确认产品");
  const [material, setMaterial] = useState("待确认");
  const [variant, setVariant] = useState("");
  const [color, setColor] = useState("");
  const [diameter, setDiameter] = useState("1.75");
  const [region, setRegion] = useState("CN");
  const [stock, setStock] = useState("0");
  const [opened, setOpened] = useState("0");
  const [target, setTarget] = useState("1");
  const [threshold, setThreshold] = useState("1");
  const [weight, setWeight] = useState("1000");
  const [location, setLocation] = useState("");
  const [decision, setDecision] = useState<EvidenceCreateInput["source"]["user_decision"]>("undecided");

  const applyResult = (next: ImageRecognitionResult) => {
    setResult(next);
    setBrand(next.suggested.brand || "待识别品牌");
    setProductLine(next.suggested.product_line || next.suggested.material_type || "待确认产品");
    setMaterial(next.suggested.material_type || "待确认");
    setVariant(next.suggested.variant || "");
    setColor(next.suggested.color || "");
    setDiameter(String(next.suggested.diameter_mm || 1.75));
    setSeller(next.suggested.brand || "");
    if (next.suggested.quote && /默认参数|照默认|按默认|直接用|default/i.test(next.suggested.quote)) setDecision("use_default_profile");
  };

  const selectFile = async (selected: File | null) => {
    setRecognitionError(null);
    setResult(null);
    setFile(selected);
    if (!selected) return;
    if (!selected.type.startsWith("image/")) {
      setFile(null);
      setRecognitionError("智能建档目前需要PNG、JPG或WebP图片；PDF可以在耗材详情页作为原始资料保存。 ");
      return;
    }
    if (selected.size > 8 * 1024 * 1024) {
      setFile(null);
      setRecognitionError("图片超过8MB，请裁剪或压缩后再试。 ");
      return;
    }
    setRecognizing(true);
    try {
      const next = await dashboardApi.recognizeImage({ file: { filename: "recognition.png", media_type: "image/png", data_base64: await normalizedImageBase64(selected) } });
      applyResult(next);
    } catch (caught) {
      setRecognitionError(userMessage(caught));
    } finally {
      setRecognizing(false);
    }
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    if (!file || !result || recognizing) return;
    const claims = result.claims.filter((claim) => claim.value.trim()).map((claim) => ({ key: claim.key, value: claim.value.trim(), unit: claim.unit || null }));
    await onSubmit({
      filament: {
        fields: {
          brand: brand.trim() || "待识别品牌",
          manufacturer: null,
          seller: seller.trim() || null,
          product_line: productLine.trim() || "待确认产品",
          material_type: material.trim() || "待确认",
          variant: variant.trim() || null,
          color: color.trim() || null,
          color_family: null,
          diameter_mm: Number(diameter),
          sku: null,
          barcode: null,
          region,
          status: "staged",
        },
        stock_spools: Number(stock),
        opened_remaining_percent: Number(opened),
        spool_weight_g: Number(weight),
        low_stock_threshold: Number(threshold),
        target_stock_spools: Number(target),
        storage_location: location.trim() || null,
        inventory_notes: "图片识别生成候选草稿，已由用户确认后建档。",
      },
      evidence: {
        source: {
          scope_level: "product",
          kind: "seller",
          title: result.suggested.title || `${brand} 参数资料`,
          source_organization: seller.trim() || brand.trim() || null,
          origin: null,
          region,
          document_version: null,
          user_decision: decision,
          quote: result.suggested.quote,
          notes: result.warnings.join(" "),
        },
        claims,
        file: { filename: file.name, media_type: file.type || "image/png", data_base64: await fileToBase64(file) },
      },
    });
  };

  return <div className="modal-backdrop" role="presentation"><section className="modal-panel wide smart-import-panel" role="dialog" aria-modal="true" aria-labelledby="smart-import-title">
    <header className="modal-header"><div><p className="eyebrow">最快路径</p><h2 id="smart-import-title">从截图智能建档</h2><p>上传商家参数图，系统先识别再生成可编辑草稿；你只需要确认结果，不必逐项抄写。</p></div><button className="icon-button" type="button" onClick={onClose} aria-label="关闭" disabled={busy || recognizing}><X size={20} /></button></header>
    <form className="modal-form" onSubmit={(event) => void submit(event)}>
      <div className="smart-import-upload"><label className="upload-dropzone"><MagnifyingGlass size={28} /><strong>{file ? file.name : "选择一张商家参数截图"}</strong><span>{recognizing ? "正在识别图片…" : file ? "可以重新选择图片" : "支持 PNG、JPG、WebP，最大8MB"}</span><input type="file" accept="image/png,image/jpeg,image/webp" onChange={(event) => void selectFile(event.target.files?.[0] || null)} /></label>{recognitionError && <p className="field-error">{recognitionError}</p>}{result && <div className="recognition-summary"><strong>已识别 {result.claims.length} 个参数</strong><span>{result.engine} · 结果仍需核对</span>{result.warnings.map((warning) => <small key={warning}>{warning}</small>)}</div>}</div>
      <div className="filament-form-grid">
        <SelectOrCustomInput label="品牌（识别草稿）" value={brand} onChange={setBrand} options={distinctValues(rows, "brand")} />
        <SelectOrCustomInput label="销售商/厂家" value={seller} onChange={setSeller} options={distinctValues(rows, "seller")} />
        <SelectOrCustomInput label="产品线（识别草稿）" value={productLine} onChange={setProductLine} options={distinctValues(rows, "product_line")} />
        <label><span>材料</span><select value={material} onChange={(event) => setMaterial(event.target.value)}>{[...MATERIAL_OPTIONS, "待确认"].map((item) => <option key={item}>{item}</option>)}</select></label>
        <SelectOrCustomInput label="型号/变体" value={variant} onChange={setVariant} options={distinctValues(rows, "variant")} />
        <SelectOrCustomInput label="颜色" value={color} onChange={setColor} options={distinctValues(rows, "color", COMMON_COLORS)} />
        <label><span>线径</span><select value={diameter} onChange={(event) => setDiameter(event.target.value)}><option value="1.75">1.75 毫米</option><option value="2.85">2.85 毫米</option></select></label>
        <label><span>资料地区</span><select value={region} onChange={(event) => setRegion(event.target.value)}>{REGION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}（{value}）</option>)}</select></label>
        <label><span>未开封整卷</span><input type="number" min="0" max="10000" required value={stock} onChange={(event) => setStock(event.target.value)} /><small>图片通常不能代表实际库存，默认0。</small></label>
        <label><span>一卷在用余量（%）</span><input type="number" min="0" max="100" step="5" required value={opened} onChange={(event) => setOpened(event.target.value)} /></label>
        <label><span>目标库存（卷）</span><input type="number" min="0" max="10000" required value={target} onChange={(event) => setTarget(event.target.value)} /></label>
        <label><span>低库存阈值（卷）</span><input type="number" min="0" max="10000" required value={threshold} onChange={(event) => setThreshold(event.target.value)} /></label>
        <label><span>单卷净重（克）</span><input type="number" min="1" max="100000" required value={weight} onChange={(event) => setWeight(event.target.value)} /></label>
        <label><span>存放位置</span><input maxLength={200} value={location} onChange={(event) => setLocation(event.target.value)} /></label>
        <label><span>采用决定</span><select value={decision} onChange={(event) => setDecision(event.target.value as EvidenceCreateInput["source"]["user_decision"])}>{SOURCE_DECISION_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
      </div>
      {result && <div className="recognized-claims"><strong>识别到的原始参数</strong>{result.claims.length ? result.claims.map((claim, index) => <span key={`${claim.key}-${index}`}>{claimKeyLabel(claim.key)}：{claim.value}{claim.unit ? ` ${claim.unit}` : ""}</span>) : <span>没有识别到带标签的参数，原图仍会保存。</span>}</div>}
      <div className="modal-actions"><button className="secondary-button" type="button" onClick={onClose} disabled={busy || recognizing}>取消</button><button className="primary-button" type="submit" disabled={busy || recognizing || !file || !result}>{busy ? "保存中" : "确认建档"}</button></div>
    </form>
  </section></div>;
}

function CredentialDialog({
  username,
  busy,
  error,
  onClose,
  onSubmit,
}: {
  username: string;
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSubmit: (input: { username: string; current_password: string; new_password?: string }) => void;
}) {
  const [nextUsername, setNextUsername] = useState(username);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const mismatch = Boolean(newPassword && newPassword !== confirmation);

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel compact" role="dialog" aria-modal="true" aria-labelledby="credential-title">
        <header className="modal-header">
          <div><p className="eyebrow">账户设置</p><h2 id="credential-title">修改登录信息</h2><p>保存后所有设备需要重新登录。</p></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭" disabled={busy}><X size={20} /></button>
        </header>
        <form className="modal-form" onSubmit={(event) => {
          event.preventDefault();
          if (!mismatch) onSubmit({ username: nextUsername, current_password: currentPassword, ...(newPassword ? { new_password: newPassword } : {}) });
        }}>
          {error && <div className="auth-error" role="alert">{error}</div>}
          <label><span>用户名</span><input autoComplete="username" minLength={3} maxLength={64} required value={nextUsername} onChange={(event) => setNextUsername(event.target.value)} /></label>
          <label><span>当前密码</span><input autoComplete="current-password" type="password" required value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} /></label>
          <label><span>新密码（不修改请留空）</span><input autoComplete="new-password" type="password" minLength={10} maxLength={256} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
          <label><span>确认新密码</span><input autoComplete="new-password" type="password" minLength={10} maxLength={256} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} disabled={!newPassword} /></label>
          {mismatch && <p className="field-error">两次输入的新密码不一致。</p>}
          <div className="modal-actions">
            <button className="secondary-button" type="button" onClick={onClose} disabled={busy}>取消</button>
            <button className="primary-button" type="submit" disabled={busy || mismatch || !currentPassword}>{busy ? "保存中" : "保存并重新登录"}</button>
          </div>
        </form>
      </section>
    </div>
  );
}

function InventoryEvaluationDialog({ packet, onClose, onCopied }: { packet: AiInventoryPacket; onClose: () => void; onCopied: () => void }) {
  const copyPacket = async () => {
    await navigator.clipboard.writeText(JSON.stringify(packet));
    onCopied();
  };
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal-panel wide evaluation-panel" role="dialog" aria-modal="true" aria-labelledby="evaluation-title">
        <header className="modal-header">
          <div><p className="eyebrow">一键盘点评测</p><h2 id="evaluation-title">库存档案检查结果</h2><p>只检查库存、颜色归类与商家资料完整性，不生成打印方案。</p></div>
          <button className="icon-button" type="button" onClick={onClose} aria-label="关闭"><X size={20} /></button>
        </header>
        <div className="evaluation-content">
          <section className="evaluation-summary">
            <div><span>产品系列</span><strong>{packet.summary.series}</strong></div>
            <div><span>颜色规格</span><strong>{packet.summary.variants}</strong></div>
            <div><span>未开封</span><strong>{packet.summary.sealed}<small>卷</small></strong></div>
            <div><span>开封在用</span><strong>{packet.summary.opened}<small>卷</small></strong></div>
            <div><span>库存当量</span><strong>{packet.summary.equivalent}<small>卷</small></strong></div>
          </section>
          <section className="evaluation-actions">
            <h3>建议先处理</h3>
            {packet.actions.length ? packet.actions.map((action) => (
              <article key={action.type}><span>{action.count}</span><p>{action.message}</p></article>
            )) : <div className="evaluation-clear"><Check size={20} />当前没有需要优先处理的档案问题。</div>}
          </section>
          <div className="evaluation-ai-note">
            <Sparkle size={20} />
            <div><strong>给 AI 的紧凑数据已经准备好</strong><p>复制后可直接发给 Codex；字段稳定、无原始图片与密钥，比读取完整网页更省上下文。</p></div>
            <button className="secondary-button" type="button" onClick={() => void copyPacket()}>复制紧凑 JSON</button>
          </div>
        </div>
      </section>
    </div>
  );
}

export function InventoryDashboard({ session, onSessionEnded }: { session: SessionInfo; onSessionEnded: () => void }) {
  const initialViews = useMemo(() => loadViews(), []);
  const [views, setViews] = useState<SavedView[]>(initialViews);
  const [activeViewId, setActiveViewId] = useState(() => loadActiveView(initialViews));
  const [payload, setPayload] = useState<DashboardPayload>(EMPTY_PAYLOAD);
  const [products, setProducts] = useState<ProductCatalogPayload>(EMPTY_PRODUCTS);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [columnsOpen, setColumnsOpen] = useState(false);
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [inventoryRow, setInventoryRow] = useState<FilamentRow | null>(null);
  const [editRow, setEditRow] = useState<FilamentRow | null>(null);
  const [closing, setClosing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [page, setPage] = useState<"dashboard" | "library" | "replenishment">("library");
  const [libraryMode, setLibraryMode] = useState<"products" | "matrix" | "cards" | "table">("products");
  const [createOpen, setCreateOpen] = useState(false);
  const [smartImportOpen, setSmartImportOpen] = useState(false);
  const [evidenceOpen, setEvidenceOpen] = useState(false);
  const [detail, setDetail] = useState<FilamentDetail | null>(null);
  const [productDetail, setProductDetail] = useState<ProductDetail | null>(null);
  const [productPresetOpen, setProductPresetOpen] = useState(false);
  const [productEvidenceOpen, setProductEvidenceOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [settingsError, setSettingsError] = useState<string | null>(null);
  const [evaluation, setEvaluation] = useState<AiInventoryPacket | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [visibleFields, setVisibleFields] = useState<Set<string>>(new Set());
  const tableElement = useRef<HTMLDivElement>(null);
  const tableRef = useRef<Tabulator | null>(null);
  const tableReadyRef = useRef(false);
  const rowsRef = useRef(payload.rows);
  const viewsRef = useRef(views);
  const activeViewRef = useRef(activeViewId);
  const searchRef = useRef(search);
  const applyingView = useRef(false);
  const saveTimer = useRef<number | null>(null);
  const rowActionRef = useRef<(action: string, row: FilamentRow) => void>(() => undefined);

  useEffect(() => { viewsRef.current = views; }, [views]);
  useEffect(() => { activeViewRef.current = activeViewId; }, [activeViewId]);
  useEffect(() => { searchRef.current = search; }, [search]);
  useEffect(() => { rowsRef.current = payload.rows; }, [payload.rows]);

  const showToast = useCallback((message: string) => {
    setToast(message);
    window.setTimeout(() => setToast(null), 2800);
  }, []);

  const reportRequestError = useCallback((caught: unknown) => {
    if (caught instanceof DashboardApiError && caught.status === 401) {
      onSessionEnded();
      return;
    }
    setError(userMessage(caught));
  }, [onSessionEnded]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [data, productData] = await Promise.all([dashboardApi.list(), dashboardApi.products()]);
      setPayload(data);
      setProducts(productData);
    } catch (caught) {
      reportRequestError(caught);
    } finally {
      setLoading(false);
    }
  }, [reportRequestError]);

  const openDetail = useCallback(async (filamentId: string) => {
    setDetailLoading(true);
    setError(null);
    try { setDetail(await dashboardApi.detail(filamentId)); }
    catch (caught) { reportRequestError(caught); }
    finally { setDetailLoading(false); }
  }, [reportRequestError]);

  const openProductDetail = useCallback(async (productId: string) => {
    setDetailLoading(true);
    setError(null);
    try { setProductDetail(await dashboardApi.productDetail(productId)); }
    catch (caught) { reportRequestError(caught); }
    finally { setDetailLoading(false); }
  }, [reportRequestError]);

  const applyRowFilter = useCallback(() => {
    const table = tableRef.current;
    if (!table || !tableReadyRef.current) return;
    const active = viewsRef.current.find((view) => view.id === activeViewRef.current);
    const needle = searchRef.current.trim().toLocaleLowerCase("zh-CN");
    table.setFilter((data: FilamentRow) => {
      if (active?.preset === "low-stock" && data.stock_status === "正常") return false;
      if (!needle) return true;
      return [data.brand, data.product_line, data.material_type, data.color, data.color_family, data.variant, data.sku]
        .filter(Boolean)
        .some((value) => String(value).toLocaleLowerCase("zh-CN").includes(needle));
    });
  }, []);

  const captureView = useCallback(() => {
    const table = tableRef.current;
    if (!table || !tableReadyRef.current || applyingView.current) return;
    const id = activeViewRef.current;
    const layout = table.getColumnLayout();
    const sorters: Sorter[] = table.getSorters().map((sorter) => ({ column: sorter.field, dir: sorter.dir }));
    const headerFilters: Filter[] = table.getHeaderFilters().map((filter) => ({
      field: filter.field,
      type: filter.type,
      value: filter.value,
    }));
    const fields = layout
      .filter((column) => column.visible !== false && column.field && column.field in FIELD_LABELS)
      .map((column) => column.field!);
    setVisibleFields(new Set(fields));
    setViews((current) => {
      const next = current.map((view) =>
        view.id === id ? { ...view, layout, sorters, headerFilters, visibleFields: fields } : view,
      );
      saveViews(next);
      return next;
    });
  }, []);

  const scheduleCapture = useCallback(() => {
    if (applyingView.current) return;
    if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
    saveTimer.current = window.setTimeout(captureView, 180);
  }, [captureView]);

  const applyView = useCallback((view: SavedView) => {
    const table = tableRef.current;
    if (!table || !tableReadyRef.current) return;
    applyingView.current = true;
    table.clearHeaderFilter();
    table.setColumnLayout(view.layout || makeDefaultLayout(table, view));
    table.setSort(view.sorters || []);
    for (const filter of view.headerFilters || []) table.setHeaderFilterValue(filter.field, filter.value);
    const fields = (view.layout || [])
      .filter((column) => column.visible !== false && column.field && column.field in FIELD_LABELS)
      .map((column) => column.field!);
    setVisibleFields(new Set(fields.length ? fields : view.visibleFields));
    window.setTimeout(() => {
      applyingView.current = false;
      applyRowFilter();
    }, 0);
  }, [applyRowFilter]);

  const changeView = useCallback((id: string) => {
    captureView();
    const view = viewsRef.current.find((item) => item.id === id);
    if (!view) return;
    activeViewRef.current = id;
    setActiveViewId(id);
    saveActiveView(id);
    setSearch("");
    searchRef.current = "";
    applyView(view);
  }, [applyView, captureView]);

  const mutate = useCallback(async <T,>(operation: () => Promise<T>, message: string): Promise<T | false> => {
    setBusy(true);
    setError(null);
    try {
      const result = await operation();
      await loadData();
      setInventoryRow(null);
      showToast(message);
      return result;
    } catch (caught) {
      reportRequestError(caught);
      return false;
    } finally {
      setBusy(false);
    }
  }, [loadData, reportRequestError, showToast]);

  const submitProductPreset = useCallback(async (input: ProductPresetCreateInput) => {
    setBusy(true);
    setError(null);
    try {
      await dashboardApi.addProductPreset(input);
      await loadData();
      setProductDetail(await dashboardApi.productDetail(input.product_id));
      setProductPresetOpen(false);
      showToast("厂家预设已解析并建档");
    } catch (caught) {
      reportRequestError(caught);
    } finally {
      setBusy(false);
    }
  }, [loadData, reportRequestError, showToast]);

  const submitProductEvidence = useCallback(async (source: ProductEvidenceCreateInput["source"], files: File[]) => {
    if (!productDetail) return;
    setBusy(true);
    setError(null);
    try {
      let created = 0;
      let deduplicated = 0;
      for (const file of files) {
        const result = await dashboardApi.addProductEvidence({
          product_id: productDetail.product.id,
          source: {
            ...source,
            title: source.title ? (files.length > 1 ? `${source.title} · ${file.name}` : source.title) : file.name,
          },
          file: {
            filename: file.name,
            media_type: file.type as ProductEvidenceCreateInput["file"]["media_type"],
            data_base64: await fileToBase64(file),
          },
        });
        result.deduplicated_source ? deduplicated += 1 : created += 1;
      }
      await loadData();
      setProductDetail(await dashboardApi.productDetail(productDetail.product.id));
      setProductEvidenceOpen(false);
      showToast(`已保存 ${created} 张原图${deduplicated ? `，跳过 ${deduplicated} 张重复图片` : ""}`);
    } catch (caught) {
      reportRequestError(caught);
    } finally {
      setBusy(false);
    }
  }, [loadData, productDetail, reportRequestError, showToast]);

  const submitSmartImport = useCallback(async (input: SmartImportSubmission) => {
    setBusy(true);
    setError(null);
    let filamentId: string | null = null;
    try {
      const created = await dashboardApi.createFilament(input.filament) as { filament_id?: string; id?: string };
      filamentId = created.filament_id || created.id || null;
      if (!filamentId) throw new Error("建档接口没有返回耗材ID。");
      try {
        await dashboardApi.addEvidence({ filament_id: filamentId, ...input.evidence });
      } catch (caught) {
        // 两个接口不能跨请求共享SQLite事务；保留已建立的草稿，并引导用户从详情页补传，避免重复建档。
        await loadData();
        setSmartImportOpen(false);
        setError(`耗材已建档，但原图资料未保存：${userMessage(caught)}。请在详情页点击“添加厂家资料”重试。`);
        await openDetail(filamentId);
        return;
      }
      await loadData();
      setSmartImportOpen(false);
      showToast("已识图建档，原图和参数已保存");
      await openDetail(filamentId);
    } catch (caught) {
      reportRequestError(caught);
    } finally {
      setBusy(false);
    }
  }, [loadData, openDetail, reportRequestError, showToast]);

  rowActionRef.current = (action, row) => {
    if (busy) return;
    if (action === "edit") setEditRow(row);
    if (action === "increment") void mutate(() => dashboardApi.adjust(row.filament_id, 1), "库存已增加1卷");
    if (action === "set") setInventoryRow(row);
  };

  useEffect(() => {
    // Tabulator needs a visible container to measure and build its columns.
    // Initialising it while the product view keeps the table off-screen can
    // leave an empty stage, especially on narrow mobile viewports.
    if (libraryMode !== "table" || !tableElement.current) return;
    const table = new Tabulator(tableElement.current, {
      data: [],
      index: "filament_id",
      layout: "fitDataStretch",
      height: "min(62dvh, 720px)",
      movableColumns: true,
      resizableColumnFit: false,
      placeholder: "没有符合当前视图的耗材",
      columns: makeColumns((action, row) => rowActionRef.current(action, row)),
    });
    tableRef.current = table;
    table.on("tableBuilt", () => {
      tableReadyRef.current = true;
      const view = viewsRef.current.find((item) => item.id === activeViewRef.current) || DEFAULT_VIEWS[0];
      applyView(view);
      void table.replaceData(rowsRef.current);
    });
    table.on("columnMoved", scheduleCapture);
    table.on("columnResized", scheduleCapture);
    table.on("columnVisibilityChanged", scheduleCapture);
    table.on("dataSorted", scheduleCapture);
    table.on("dataFiltered", scheduleCapture);
    return () => {
      if (saveTimer.current !== null) window.clearTimeout(saveTimer.current);
      table.destroy();
      tableRef.current = null;
      tableReadyRef.current = false;
    };
  }, [applyView, libraryMode, scheduleCapture]);

  useEffect(() => { void loadData(); }, [loadData]);
  useEffect(() => {
    if (tableRef.current && tableReadyRef.current) void tableRef.current.replaceData(payload.rows);
  }, [payload.rows]);
  useEffect(() => { applyRowFilter(); }, [search, applyRowFilter]);

  const toggleColumn = (field: string) => {
    const column = tableRef.current?.getColumn(field);
    if (!column) return;
    column.toggle();
    setVisibleFields((current) => {
      const next = new Set(current);
      if (column.isVisible()) next.add(field); else next.delete(field);
      return next;
    });
    scheduleCapture();
  };

  const createView = (name: string) => {
    captureView();
    const table = tableRef.current;
    if (!table) return;
    const id = `custom-${crypto.randomUUID()}`;
    const view: SavedView = {
      id,
      name,
      builtIn: false,
      preset: "custom",
      visibleFields: [...visibleFields],
      layout: table.getColumnLayout(),
      sorters: table.getSorters().map((sorter) => ({ column: sorter.field, dir: sorter.dir })),
      headerFilters: table.getHeaderFilters(),
    };
    const next = [...viewsRef.current, view];
    viewsRef.current = next;
    setViews(next);
    saveViews(next);
    setViewDialogOpen(false);
    changeView(id);
    showToast(`已创建视图“${name}”`);
  };

  const deleteActiveView = () => {
    const active = views.find((view) => view.id === activeViewId);
    if (!active || active.builtIn) return;
    const next = views.filter((view) => view.id !== activeViewId);
    viewsRef.current = next;
    setViews(next);
    saveViews(next);
    changeView("inventory");
    showToast("自定义视图已删除");
  };

  const resetAllViews = () => {
    const next = resetViews();
    viewsRef.current = next;
    setViews(next);
    activeViewRef.current = "inventory";
    setActiveViewId("inventory");
    applyView(next[0]);
    showToast("视图布局已恢复默认");
  };

  const shutdown = async () => {
    setClosing(true);
    try { await dashboardApi.shutdown(); } catch { /* server may close before response flush */ }
  };

  const logout = async () => {
    setBusy(true);
    try { await dashboardApi.logout(); } finally { setBusy(false); onSessionEnded(); }
  };

  const updateCredentials = async (input: { username: string; current_password: string; new_password?: string }) => {
    setBusy(true);
    setSettingsError(null);
    try {
      await dashboardApi.updateCredentials(input);
      setSettingsOpen(false);
      onSessionEnded();
    } catch (caught) {
      setSettingsError(userMessage(caught));
    } finally {
      setBusy(false);
    }
  };

  const openEvaluation = async () => {
    setEvaluating(true);
    setError(null);
    try {
      setEvaluation(await dashboardApi.aiInventory());
    } catch (caught) {
      reportRequestError(caught);
    } finally {
      setEvaluating(false);
    }
  };

  if (closing) {
    return (
      <main className="closing-screen min-h-[100dvh]">
        <div><p className="eyebrow">PrintPilot</p><h1>耗材看板已关闭</h1><p>本地程序已经停止，现在可以关闭这个标签页。</p></div>
      </main>
    );
  }

  const activeView = views.find((view) => view.id === activeViewId);
  const filteredRows = payload.rows.filter((row) => matchesSearch(row, search));

  return (
    <div className="app-shell min-h-[100dvh]">
      {sidebarOpen && <button className="sidebar-scrim" type="button" aria-label="关闭导航" onClick={() => setSidebarOpen(false)} />}
      <aside className={`admin-sidebar ${sidebarOpen ? "open" : ""}`} aria-label="主导航">
        <div className="sidebar-brand">
          <div className="brand-mark">PP</div>
          <div><p>PrintPilot</p><strong>耗材实验室</strong></div>
          <button className="sidebar-close" type="button" aria-label="关闭导航" onClick={() => setSidebarOpen(false)}><X size={19} /></button>
        </div>
        <nav className="sidebar-nav">
          <p className="sidebar-label">工作台</p>
          <button className={page === "dashboard" ? "active" : ""} type="button" onClick={() => { setPage("dashboard"); setSidebarOpen(false); }}><Package size={19} />工作台</button>
          <button className={page === "library" ? "active" : ""} type="button" onClick={() => { setPage("library"); setSidebarOpen(false); }}><Table size={19} />耗材库</button>
          <button className={page === "replenishment" ? "active" : ""} type="button" onClick={() => { setPage("replenishment"); setSidebarOpen(false); }}><ShoppingCart size={19} />补货清单{payload.summary.replenishment_spools > 0 && <span className="nav-count">{payload.summary.replenishment_spools}</span>}</button>
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-user"><span>{(session.username || "P").slice(0, 1).toUpperCase()}</span><div><strong>{session.username || "本地用户"}</strong><small>{session.mode === "password" ? "密码保护" : "本地安全连接"}</small></div></div>
          {session.mode === "password" ? <>
            <button type="button" onClick={() => { setSettingsError(null); setSettingsOpen(true); }}><GearSix size={18} />账户设置</button>
            <button type="button" onClick={() => void logout()}><SignOut size={18} />退出登录</button>
          </> : <button type="button" onClick={() => void shutdown()}><Power size={18} />关闭看板</button>}
        </div>
      </aside>

      <div className="admin-content">
        <header className="topbar">
          <div className="page-heading">
            <button className="menu-button" type="button" aria-label="打开导航" onClick={() => setSidebarOpen(true)}><List size={21} /></button>
            <label className="search-control header-search">
              <MagnifyingGlass size={18} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索耗材" aria-label="全局搜索耗材" />
              {search && <button type="button" onClick={() => setSearch("")} aria-label="清除搜索"><X size={15} /></button>}
            </label>
          </div>
          <div className="topbar-actions">
            <span className="connection-status"><span />本地数据已连接</span>
            <button className="icon-button" type="button" onClick={() => void loadData()} disabled={loading} aria-label="刷新数据"><ArrowsClockwise size={18} className={loading ? "spin" : ""} /></button>
          </div>
        </header>

        <main className="dashboard-main">
        {error && <div className="error-banner global-error" role="alert"><WarningCircle size={20} /><span>{error}</span><button type="button" onClick={() => { setError(null); void loadData(); }}>重试</button></div>}
        {detail ? <DetailPage detail={detail} busy={busy} onBack={() => setDetail(null)} onEdit={() => setEditRow(detail.filament)} onCount={() => setInventoryRow(detail.filament)} onAddEvidence={() => setEvidenceOpen(true)} onUndo={(movementId) => void mutate(() => dashboardApi.undo(movementId), "库存操作已撤销").then(async (saved) => { if (saved) setDetail(await dashboardApi.detail(detail.filament.filament_id)); })} /> : productDetail ? <ProductDetailPage detail={productDetail} busy={busy} onBack={() => setProductDetail(null)} onOpenColor={(id) => void openDetail(id)} onCount={setInventoryRow} onAddPreset={() => setProductPresetOpen(true)} onAddEvidence={() => setProductEvidenceOpen(true)} /> : <>
        {page === "dashboard" && <section className="overview-page">
          <div className="workspace-heading"><div><p className="eyebrow">PrintPilot</p><h2>耗材工作台</h2><p className="page-description">管理未开封库存、当前在用卷余量、商家颜色名与原始资料。</p></div><div className="heading-actions"><Button onClick={() => setSmartImportOpen(true)}><MagnifyingGlass />从截图建档</Button><Button variant="outline" onClick={() => setCreateOpen(true)}><Plus />手动新增</Button><Button variant="outline" disabled={evaluating} onClick={() => void openEvaluation()}><Sparkle />{evaluating ? "正在检查" : "一键评测"}</Button><Button variant="outline" onClick={() => { setPage("library"); setLibraryMode("matrix"); }}><Table />库存矩阵</Button></div></div>
          <section className="summary-strip" aria-label="库存摘要">
            <div><Package size={19} /><span>产品系列</span><strong>{payload.summary.product_series_count}</strong></div>
            <div><Stack size={19} /><span>库存当量</span><strong>{payload.summary.stock_equivalent}<small>卷</small></strong></div>
            <div><ShoppingCart size={19} /><span>建议补货</span><strong>{payload.summary.replenishment_spools}<small>卷</small></strong></div>
            <div className={payload.summary.needs_attention_count ? "attention" : ""}><WarningCircle size={19} /><span>待处理</span><strong>{payload.summary.needs_attention_count}<small>种</small></strong></div>
          </section>
          <div className="overview-grid">
            <Card><CardHeader><CardTitle>待处理事项</CardTitle><CardDescription>只提示档案缺口，不推断打印参数。</CardDescription></CardHeader><CardContent><div className="attention-list">{payload.rows.filter((row) => row.source_count === 0 || row.conflict_count > 0 || row.color_family === "未分类").slice(0, 8).map((row) => <button key={row.filament_id} type="button" onClick={() => void openDetail(row.filament_id)}><span className="readiness-dot readiness-missing_profile" /><div><strong>{row.brand} · {row.product_line} · {row.color || "未记录颜色"}</strong><small>{row.conflict_count > 0 ? `${row.conflict_count} 个商家参数冲突` : row.color_family === "未分类" ? "颜色尚未归入标准色系" : "尚未上传商家资料"}</small></div><span>查看</span></button>)}{payload.summary.needs_attention_count === 0 && <p className="empty-note">当前档案信息完整。</p>}</div></CardContent></Card>
            <Card><CardHeader><CardTitle>快捷操作</CardTitle><CardDescription>围绕建档、盘点和资料完整性完成闭环。</CardDescription></CardHeader><CardContent><div className="quick-actions"><button type="button" onClick={() => setSmartImportOpen(true)}><MagnifyingGlass size={20} /><strong>截图智能建档</strong><span>识别结果先成为草稿，确认后才保存</span></button><button type="button" onClick={() => { setPage("library"); setLibraryMode("matrix"); }}><Scales size={20} /><strong>库存矩阵盘点</strong><span>按产品和色系快速核对未开封与在用卷</span></button><button type="button" onClick={() => void openEvaluation()}><Sparkle size={20} /><strong>一键盘点评测</strong><span>检查颜色归类、商家资料和库存结构</span></button></div></CardContent></Card>
          </div>
        </section>}

        {page === "replenishment" && <section className="overview-page"><div className="workspace-heading"><div><p className="eyebrow">库存计划</p><h2>补货清单</h2></div><p>目标库存减去当前库存；不推算使用速度。</p></div><div className="replenishment-list">{payload.rows.filter((row) => row.replenishment_spools > 0).sort((a,b) => b.replenishment_spools - a.replenishment_spools).map((row) => <article key={row.filament_id}><div className="material-swatch" style={{backgroundColor: colorPreview(row.color)}} /><div><h3>{row.brand} · {row.product_line}</h3><p>{row.material_type} · {row.color || "未记录颜色"} · {row.storage_location || "未设置位置"}</p></div><div className="stock-gap"><span>{row.stock_spools} / {row.target_stock_spools} 卷</span><strong>补 {row.replenishment_spools} 卷</strong></div><button className="secondary-button" type="button" onClick={() => void openDetail(row.filament_id)}>详情</button><button className="primary-button" type="button" onClick={() => void mutate(() => dashboardApi.move(row.filament_id, row.replenishment_spools, "purchase", "按补货清单入库"), `已为${row.brand}增加${row.replenishment_spools}卷`)}>确认入库</button></article>)}{payload.summary.replenishment_spools === 0 && <div className="empty-state"><Check size={28} /><h3>当前无需补货</h3><p>所有耗材均达到目标库存。</p></div>}</div></section>}

        <section className={`workspace ${page === "library" ? "" : "workspace-hidden"}`}>
          <div className="workspace-heading">
            <div><p className="eyebrow">个人耗材库</p><h2>{libraryMode === "products" ? "产品目录" : activeView?.name || "库存盘点"}</h2></div>
            <div className="heading-actions"><button className="primary-button" type="button" onClick={() => setSmartImportOpen(true)}><MagnifyingGlass size={17} />从截图建档</button><button className="secondary-button" type="button" onClick={() => setCreateOpen(true)}><Plus size={17} />手动新增</button><button className="secondary-button" type="button" disabled={evaluating} onClick={() => void openEvaluation()}><Sparkle size={17} />一键评测</button><div className="segmented"><button className={libraryMode === "products" ? "active" : ""} type="button" onClick={() => setLibraryMode("products")}><Package size={16} />产品</button><button className={libraryMode === "matrix" ? "active" : ""} type="button" onClick={() => setLibraryMode("matrix")}><Table size={16} />盘点</button><button className={libraryMode === "table" ? "active" : ""} type="button" onClick={() => setLibraryMode("table")}><ListBullets size={16} />明细</button></div></div>
          </div>

          {libraryMode !== "products" && <div className="view-tabs" role="tablist" aria-label="耗材视图">
            {views.map((view) => (
              <button key={view.id} type="button" role="tab" aria-selected={activeViewId === view.id} onClick={() => changeView(view.id)}>
                {view.name}
              </button>
            ))}
            <button className="add-view" type="button" onClick={() => setViewDialogOpen(true)}><Plus size={15} />新视图</button>
          </div>}

          <section className="summary-strip compact-summary" aria-label="库存摘要">
            <div><Package size={19} /><span>颜色规格</span><strong>{payload.summary.color_variant_count}</strong></div>
            <div><Stack size={19} /><span>库存当量</span><strong>{payload.summary.stock_equivalent}<small>卷</small></strong></div>
            <div><Scales size={19} /><span>库存净重</span><strong>{payload.summary.stock_total_kg.toFixed(3)}<small>千克</small></strong></div>
            <div><WarningCircle size={19} /><span>开封在用</span><strong>{payload.summary.opened_spool_count}<small>卷</small></strong></div>
          </section>

          {libraryMode === "products" && <ProductCatalog products={products.rows} search={search} onOpen={(id) => void openProductDetail(id)} />}

          {libraryMode === "matrix" && <InventoryMatrix rows={filteredRows} onInventory={setInventoryRow} onDetail={(row) => void openDetail(row.filament_id)} />}

          {libraryMode === "cards" && <div className="material-card-grid">{filteredRows.map((row) => <article className="material-card" key={row.filament_id}><header><div className="material-swatch" style={{backgroundColor: colorPreview(row.color)}} /><div><h3>{row.brand}</h3><p>{row.product_line}</p></div><span className="readiness-badge readiness-official_profile">{row.color_family}</span></header><dl><div><dt>材料</dt><dd>{row.material_type}</dd></div><div><dt>商家颜色名</dt><dd>{row.color || "—"}</dd></div><div><dt>未开封</dt><dd>{row.stock_spools} 卷</dd></div><div><dt>在用卷</dt><dd>{row.opened_remaining_percent ? `${row.opened_remaining_percent}%` : "无"}</dd></div><div><dt>库存当量</dt><dd>{row.stock_equivalent} 卷</dd></div><div><dt>商家资料</dt><dd>{row.source_count ? `${row.source_count} 份` : "未上传"}</dd></div></dl><div className="card-actions"><button className="secondary-button" type="button" onClick={() => void openDetail(row.filament_id)}>详情</button><button className="secondary-button" type="button" disabled={busy} onClick={() => void mutate(() => dashboardApi.move(row.filament_id, 1, "purchase", "网页快捷入库"), "库存已增加1卷")}>+1 入库</button><button className="primary-button" type="button" onClick={() => setInventoryRow(row)}>盘点</button></div></article>)}{payload.rows.length === 0 && <div className="empty-state"><Package size={28} /><h3>还没有耗材</h3><p>上传一张商家参数图，系统会先识别为候选草稿，由你确认后建档。</p><button className="primary-button" type="button" onClick={() => setSmartImportOpen(true)}>从截图建档</button></div>}</div>}

          <div className={`table-view ${libraryMode === "table" ? "" : "view-hidden"}`}><div className="table-toolbar">
            <label className="search-control table-search">
              <MagnifyingGlass size={18} />
              <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索品牌、材料、颜色或SKU" aria-label="搜索耗材" />
              {search && <button type="button" onClick={() => setSearch("")} aria-label="清除搜索"><X size={15} /></button>}
            </label>
            <div className="toolbar-actions">
              <button className="secondary-button" type="button" onClick={() => setColumnsOpen(!columnsOpen)}><Columns size={17} />字段</button>
              <button className="secondary-button" type="button" onClick={() => { captureView(); showToast("当前视图已保存"); }}><FloppyDisk size={17} />保存布局</button>
              <button className="secondary-button" type="button" onClick={() => void loadData()} disabled={loading}><ArrowsClockwise size={17} className={loading ? "spin" : ""} />刷新</button>
              {!activeView?.builtIn && <button className="danger-button" type="button" onClick={deleteActiveView}><Trash size={17} />删除视图</button>}
            </div>
          </div>

          {columnsOpen && (
            <aside className="column-panel" aria-label="显示字段">
              <div className="column-panel-title"><div><p className="eyebrow">当前视图</p><h3>选择显示字段</h3></div><button className="icon-button" type="button" onClick={() => setColumnsOpen(false)} aria-label="关闭字段选择"><X size={19} /></button></div>
              <div className="column-grid">
                {FIELD_ORDER.map((field) => (
                  <label key={field}><input type="checkbox" checked={visibleFields.has(field)} onChange={() => toggleColumn(field)} /><span>{FIELD_LABELS[field]}</span></label>
                ))}
              </div>
              <button className="text-button" type="button" onClick={resetAllViews}>恢复全部默认视图</button>
            </aside>
          )}

          <div className="table-stage" aria-busy={loading || busy}>
            {(loading || busy) && <div className="table-loading"><span /><span /><span /><p>{busy ? "正在保存库存" : "正在读取耗材档案"}</p></div>}
            <div ref={tableElement} />
          </div>
          <footer className="workspace-footer"><span>双击列间分隔线调整宽度；拖动表头改变顺序；表头输入框用于字段筛选。</span><span>{payload.rows.length} 条耗材档案</span></footer>
          </div>
        </section>
        </>}
        </main>
      </div>

      {inventoryRow && <InventoryDialog row={inventoryRow} busy={busy} onClose={() => setInventoryRow(null)} onSubmit={(input) => void mutate(() => dashboardApi.set(input), "库存盘点已保存")} />}
      {editRow && <FilamentDialog row={editRow} rows={payload.rows} busy={busy} onClose={() => setEditRow(null)} onSubmit={(input) => void mutate(() => dashboardApi.updateFilament(input), "耗材档案已更新").then((saved) => { if (saved) setEditRow(null); })} />}
      {createOpen && <CreateFilamentDialog rows={payload.rows} busy={busy} onClose={() => setCreateOpen(false)} onSubmit={(input) => void mutate(() => dashboardApi.createFilament(input), "耗材已创建").then((saved) => { if (saved) setCreateOpen(false); })} />}
      {smartImportOpen && <SmartImportDialog rows={payload.rows} busy={busy} onClose={() => setSmartImportOpen(false)} onSubmit={submitSmartImport} />}
      {evidenceOpen && detail && <EvidenceDialog detail={detail} busy={busy} onClose={() => setEvidenceOpen(false)} onSubmit={(input) => mutate(() => dashboardApi.addEvidence(input), "资料已保存").then((saved) => { if (saved) { setEvidenceOpen(false); void openDetail(detail.filament.filament_id); } })} />}
      {productEvidenceOpen && productDetail && <ProductEvidenceDialog detail={productDetail} busy={busy} onClose={() => setProductEvidenceOpen(false)} onSubmit={submitProductEvidence} />}
      {productPresetOpen && productDetail && <ProductPresetDialog detail={productDetail} busy={busy} onClose={() => setProductPresetOpen(false)} onSubmit={submitProductPreset} />}
      {detailLoading && <div className="detail-loading" aria-live="polite">正在读取耗材详情</div>}
      {viewDialogOpen && <ViewNameDialog onClose={() => setViewDialogOpen(false)} onSubmit={createView} />}
      {settingsOpen && <CredentialDialog username={session.username || ""} busy={busy} error={settingsError} onClose={() => setSettingsOpen(false)} onSubmit={(input) => void updateCredentials(input)} />}
      {evaluation && <InventoryEvaluationDialog packet={evaluation} onClose={() => setEvaluation(null)} onCopied={() => showToast("已复制 AI 紧凑数据")} />}
      <div className={`toast ${toast ? "visible" : ""}`} aria-live="polite">{toast && <><Check size={17} />{toast}</>}</div>
    </div>
  );
}
