import type { SavedView } from "./types";

const STORAGE_KEY = "printpilot.material-dashboard.views.v1";
const ACTIVE_VIEW_KEY = "printpilot.material-dashboard.active-view.v1";

export const FIELD_LABELS: Record<string, string> = {
  brand: "品牌",
  manufacturer: "制造商",
  seller: "销售商",
  product_line: "产品线",
  material_type: "材料",
  variant: "型号",
  color: "颜色",
  color_family: "色系",
  diameter_mm: "线径（毫米）",
  sku: "SKU",
  barcode: "条码",
  region: "地区",
  status: "档案状态",
  stock_spools: "未开封（卷）",
  opened_remaining_percent: "在用卷余量（%）",
  stock_equivalent: "库存当量（卷）",
  spool_weight_g: "单卷净重（克）",
  stock_total_kg: "总重量（千克）",
  low_stock_threshold: "低库存阈值",
  target_stock_spools: "目标库存（卷）",
  replenishment_spools: "待补货（卷）",
  storage_location: "存放位置",
  inventory_notes: "库存备注",
  stock_status: "库存状态",
  readiness_label: "打印准备状态",
  conflict_count: "冲突项",
  created_at: "建档时间",
  inventory_updated_at: "库存更新时间",
  filament_id: "耗材ID",
};

export const FIELD_ORDER = Object.keys(FIELD_LABELS);

const inventoryFields = [
  "brand",
  "product_line",
  "material_type",
  "color",
  "color_family",
  "stock_spools",
  "opened_remaining_percent",
  "stock_equivalent",
  "spool_weight_g",
  "stock_total_kg",
  "target_stock_spools",
  "replenishment_spools",
  "storage_location",
  "stock_status",
  "readiness_label",
];

const catalogFields = [
  "brand",
  "manufacturer",
  "seller",
  "product_line",
  "material_type",
  "variant",
  "color",
  "color_family",
  "diameter_mm",
  "sku",
  "region",
  "status",
];

export const DEFAULT_VIEWS: SavedView[] = [
  {
    id: "inventory",
    name: "库存盘点",
    builtIn: true,
    preset: "inventory",
    visibleFields: inventoryFields,
  },
  {
    id: "low-stock",
    name: "低库存",
    builtIn: true,
    preset: "low-stock",
    visibleFields: inventoryFields,
  },
  {
    id: "catalog",
    name: "耗材档案",
    builtIn: true,
    preset: "catalog",
    visibleFields: catalogFields,
  },
  {
    id: "all",
    name: "全部字段",
    builtIn: true,
    preset: "all",
    visibleFields: FIELD_ORDER,
  },
];

export function loadViews(): SavedView[] {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]") as SavedView[];
    if (!Array.isArray(stored)) return DEFAULT_VIEWS;
    const storedById = new Map(stored.map((view) => [view.id, view]));
    const builtIns = DEFAULT_VIEWS.map((view) => ({
      ...view,
      ...storedById.get(view.id),
      builtIn: true,
      name: view.name,
      preset: view.preset,
    }));
    const customs = stored.filter((view) => !DEFAULT_VIEWS.some((item) => item.id === view.id));
    return [...builtIns, ...customs];
  } catch {
    return DEFAULT_VIEWS;
  }
}

export function saveViews(views: SavedView[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(views));
}

export function loadActiveView(views: SavedView[]): string {
  const stored = localStorage.getItem(ACTIVE_VIEW_KEY);
  return views.some((view) => view.id === stored) ? stored! : "inventory";
}

export function saveActiveView(id: string): void {
  localStorage.setItem(ACTIVE_VIEW_KEY, id);
}

export function resetViews(): SavedView[] {
  localStorage.removeItem(STORAGE_KEY);
  localStorage.setItem(ACTIVE_VIEW_KEY, "inventory");
  return DEFAULT_VIEWS;
}
