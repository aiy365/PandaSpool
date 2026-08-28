import type { ColumnLayout, Filter, Sorter } from "tabulator-tables";

export interface FilamentRow {
  filament_id: string;
  product_id: string | null;
  brand: string | null;
  manufacturer: string | null;
  seller: string | null;
  product_line: string | null;
  material_type: string | null;
  variant: string | null;
  color: string | null;
  color_family: string;
  diameter_mm: number;
  sku: string | null;
  barcode: string | null;
  region: string | null;
  status: string | null;
  stock_spools: number;
  sealed_spools: number;
  opened_remaining_percent: number;
  has_opened_spool: boolean;
  stock_equivalent: number;
  spool_weight_g: number;
  stock_total_kg: number;
  low_stock_threshold: number;
  target_stock_spools: number;
  replenishment_spools: number;
  storage_location: string | null;
  inventory_notes: string | null;
  stock_status: "正常" | "低库存" | "无库存";
  readiness_state: string;
  readiness_label: string;
  profile_count: number;
  calibration_count: number;
  conflict_count: number;
  source_count: number;
  claim_count: number;
  created_at: string | null;
  inventory_updated_at: string | null;
}

export interface InventorySummary {
  filament_count: number;
  stock_spools: number;
  opened_spool_count: number;
  stock_equivalent: number;
  product_series_count: number;
  color_variant_count: number;
  unclassified_color_count: number;
  stock_total_kg: number;
  low_stock_count: number;
  replenishment_spools: number;
  needs_attention_count: number;
}

export interface DashboardPayload {
  rows: FilamentRow[];
  summary: InventorySummary;
}

export interface ApiEnvelope<T> {
  data: T;
  request_id: string;
}

export interface ApiErrorPayload {
  error?: {
    code?: string;
    message?: string;
  };
  request_id?: string;
}

export type ViewPreset = "inventory" | "low-stock" | "catalog" | "all" | "custom";

export interface SavedView {
  id: string;
  name: string;
  builtIn: boolean;
  preset: ViewPreset;
  visibleFields: string[];
  layout?: ColumnLayout[];
  sorters?: Sorter[];
  headerFilters?: Filter[];
}

export interface InventorySetInput {
  filament_id: string;
  stock_spools: number;
  opened_remaining_percent: number;
  spool_weight_g: number;
  low_stock_threshold: number;
  target_stock_spools?: number;
  storage_location?: string | null;
  inventory_notes?: string | null;
  movement_note?: string | null;
}

export interface InventoryMovement {
  id: string;
  filament_id: string;
  movement_type: "purchase" | "usage" | "count" | "correction" | "undo";
  delta: number;
  before_spools: number;
  after_spools: number;
  note: string | null;
  reverses_movement_id: string | null;
  created_at: string;
}

export interface FilamentDetail {
  filament: FilamentRow;
  profiles: Array<Record<string, unknown>>;
  calibrations: Array<Record<string, unknown>>;
  claims: ClaimRecord[];
  sources: EvidenceSource[];
  movements: InventoryMovement[];
}

export interface EvidenceSource {
  id: string;
  scope_level: "product" | "color_variant";
  kind: string;
  title: string | null;
  origin: string | null;
  source_organization: string | null;
  region: string | null;
  document_version: string | null;
  retrieved_at: string | null;
  media_type: string | null;
  sha256: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  file_url: string;
}

export interface ClaimRecord {
  id: string;
  claim_key: string;
  value: unknown;
  unit: string | null;
  scope: Record<string, unknown>;
  authority: string | null;
  review_status: string;
  notes: string | null;
  source?: EvidenceSource | null;
}

export interface EvidenceClaimInput {
  key: string;
  value: string;
  unit?: string | null;
  notes?: string | null;
}

export interface EvidenceCreateInput {
  filament_id: string;
  source: {
    scope_level: "product" | "color_variant";
    kind: "manufacturer" | "seller" | "customer_service" | "official_profile" | "user_note";
    title: string;
    origin?: string | null;
    source_organization?: string | null;
    region?: string | null;
    document_version?: string | null;
    user_decision: "undecided" | "use_default_profile" | "reference_only" | "needs_validation";
    quote?: string | null;
    notes?: string | null;
  };
  claims: EvidenceClaimInput[];
  file?: {
    filename: string;
    media_type: string;
    data_base64: string;
  };
}

export interface ImageRecognitionResult {
  raw_text: string;
  claims: EvidenceClaimInput[];
  suggested: {
    brand: string | null;
    product_line: string | null;
    material_type: string | null;
    variant: string | null;
    color: string | null;
    diameter_mm: number | null;
    quote: string | null;
    title: string;
  };
  warnings: string[];
  engine: string;
}

export interface FilamentCreateInput {
  fields: FilamentUpdateInput["fields"];
  stock_spools: number;
  opened_remaining_percent: number;
  spool_weight_g: number;
  low_stock_threshold: number;
  target_stock_spools: number;
  storage_location: string | null;
  inventory_notes: string | null;
}

export interface FilamentUpdateInput {
  filament_id: string;
  fields: {
    brand: string;
    manufacturer: string | null;
    seller: string | null;
    product_line: string;
    material_type: string;
    variant: string | null;
    color: string | null;
    color_family: string | null;
    diameter_mm: number;
    sku: string | null;
    barcode: string | null;
    region: string;
    status: string;
  };
}

export interface AiInventoryAction {
  type: "opened_first" | "color_review" | "source_missing" | "duplicate_review";
  count: number;
  message: string;
}

export interface AiInventoryPacket {
  v: number;
  summary: {
    series: number;
    variants: number;
    sealed: number;
    opened: number;
    equivalent: number;
  };
  actions: AiInventoryAction[];
  items: Array<{
    id: string;
    product: string;
    material: string | null;
    color: string | null;
    family: string;
    sealed: number;
    opened_pct: number;
    sources: number;
  }>;
}


export interface ProductSummary {
  product_id: string;
  brand: string;
  manufacturer: string | null;
  seller: string | null;
  product_line: string;
  material_type: string;
  formulation: string | null;
  diameter_mm: number;
  region: string;
  status: string;
  color_count: number;
  stock_spools: number;
  opened_spool_count: number;
  stock_equivalent: number;
  source_count: number;
  claim_count: number;
  preset_count: number;
  manufacturer_preset_count: number;
  colors: FilamentRow[];
}

export interface ProductCatalogPayload {
  rows: ProductSummary[];
  summary: {
    product_count: number;
    color_count: number;
    stock_equivalent: number;
    manufacturer_preset_count: number;
  };
}

export interface PresetEvaluation {
  id: string;
  filament_id: string | null;
  scope_level: "product" | "color_variant";
  profile_name: string;
  target_printer: string;
  nozzle_mm: number;
  authority: "bambu_system" | "manufacturer_profile" | "user_profile";
  provenance: string;
  internal_origin: string | null;
  settings: Record<string, unknown>;
  warnings: string[];
  review_status: string;
  source?: EvidenceSource | null;
}

export interface ProductDetail {
  product: {
    id: string;
    brand: string;
    manufacturer: string | null;
    seller: string | null;
    product_line: string;
    material_type: string;
    formulation: string | null;
    diameter_mm: number;
    region: string;
    status: string;
  };
  colors: FilamentRow[];
  product_claims: ClaimRecord[];
  color_claims: ClaimRecord[];
  presets: PresetEvaluation[];
  sources: EvidenceSource[];
  summary: {
    color_count: number;
    stock_spools: number;
    stock_equivalent: number;
    product_claim_count: number;
    color_claim_count: number;
    preset_count: number;
  };
}

export interface ProductPresetCreateInput {
  product_id: string;
  filament_id: string | null;
  authority: "bambu_system" | "manufacturer_profile" | "user_profile";
  provenance: string;
  file: {
    filename: string;
    data_base64: string;
  };
}

export interface ProductEvidenceCreateInput {
  product_id: string;
  source: {
    kind: "manufacturer" | "seller" | "customer_service" | "user_note";
    title?: string | null;
    origin?: string | null;
    source_organization?: string | null;
    region?: string | null;
    notes?: string | null;
  };
  file: {
    filename: string;
    media_type: "image/png" | "image/jpeg" | "image/webp";
    data_base64: string;
  };
}
