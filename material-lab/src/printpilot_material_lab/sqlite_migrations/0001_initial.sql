PRAGMA foreign_keys = ON;

CREATE TABLE app_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- 厂家以“产品/配方”为单位发布的事实只保存在这里一次。
CREATE TABLE material_products (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  brand TEXT NOT NULL CHECK (length(trim(brand)) > 0),
  manufacturer TEXT,
  seller TEXT,
  product_line TEXT NOT NULL CHECK (length(trim(product_line)) > 0),
  material_type TEXT NOT NULL CHECK (length(trim(material_type)) > 0),
  formulation TEXT,
  diameter_mm REAL NOT NULL DEFAULT 1.75 CHECK (diameter_mm IN (1.75, 2.85)),
  region TEXT NOT NULL CHECK (length(trim(region)) > 0),
  status TEXT NOT NULL DEFAULT 'reviewed'
    CHECK (status IN ('staged','reviewed','calibrated','archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE UNIQUE INDEX material_products_identity_unique
  ON material_products(
    owner_id, lower(brand), lower(product_line), lower(material_type),
    lower(coalesce(formulation, '')), diameter_mm, lower(region)
  );

-- 一行代表一个可盘点的颜色库存项。品牌、材料、产品线等均由产品继承。
CREATE TABLE filaments (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  product_id TEXT NOT NULL REFERENCES material_products(id) ON DELETE RESTRICT,
  color TEXT,
  color_family TEXT,
  sku TEXT,
  barcode TEXT,
  stock_spools INTEGER NOT NULL DEFAULT 0 CHECK (stock_spools >= 0),
  opened_remaining_percent INTEGER NOT NULL DEFAULT 0
    CHECK (opened_remaining_percent BETWEEN 0 AND 100),
  spool_weight_g INTEGER NOT NULL DEFAULT 1000 CHECK (spool_weight_g > 0),
  low_stock_threshold INTEGER NOT NULL DEFAULT 1 CHECK (low_stock_threshold >= 0),
  target_stock_spools INTEGER NOT NULL DEFAULT 1 CHECK (target_stock_spools >= 0),
  storage_location TEXT,
  inventory_notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (sku IS NOT NULL OR barcode IS NOT NULL)
);
CREATE UNIQUE INDEX filaments_owner_barcode_unique
  ON filaments(owner_id, barcode) WHERE barcode IS NOT NULL;
CREATE UNIQUE INDEX filaments_product_sku_unique
  ON filaments(owner_id, product_id, sku) WHERE sku IS NOT NULL;
CREATE INDEX filaments_product_idx ON filaments(product_id);
CREATE INDEX filaments_color_family_idx ON filaments(color_family);

-- 稳定的读取投影：API仍称filament，但产品字段来自唯一产品记录。
CREATE VIEW filament_inventory_view AS
SELECT
  f.*,
  p.brand,
  p.manufacturer,
  p.seller,
  p.product_line,
  p.material_type,
  p.formulation AS variant,
  p.diameter_mm,
  p.region,
  p.status
FROM filaments f
JOIN material_products p ON p.id = f.product_id;

-- 原始证据明确绑定到产品或颜色。无参数声明的PDF/截图也不会丢失归属。
CREATE TABLE sources (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  product_id TEXT NOT NULL REFERENCES material_products(id) ON DELETE CASCADE,
  filament_id TEXT REFERENCES filaments(id) ON DELETE CASCADE,
  scope_level TEXT NOT NULL CHECK (scope_level IN ('product','color_variant')),
  kind TEXT NOT NULL,
  title TEXT,
  origin TEXT,
  source_organization TEXT,
  region TEXT,
  document_version TEXT,
  published_at TEXT,
  retrieved_at TEXT,
  media_type TEXT,
  sha256 TEXT NOT NULL CHECK (length(sha256) = 64),
  storage_path TEXT NOT NULL,
  extracted_text_path TEXT,
  metadata TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  CHECK (
    (scope_level = 'product' AND filament_id IS NULL) OR
    (scope_level = 'color_variant' AND filament_id IS NOT NULL)
  ),
  UNIQUE(owner_id, product_id, filament_id, sha256)
);
CREATE INDEX sources_product_idx ON sources(product_id);
CREATE INDEX sources_filament_idx ON sources(filament_id);
CREATE UNIQUE INDEX sources_product_hash_unique
  ON sources(owner_id, product_id, sha256)
  WHERE filament_id IS NULL;
CREATE UNIQUE INDEX sources_color_hash_unique
  ON sources(owner_id, filament_id, sha256)
  WHERE filament_id IS NOT NULL;

CREATE TABLE claims (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  product_id TEXT NOT NULL REFERENCES material_products(id) ON DELETE CASCADE,
  filament_id TEXT REFERENCES filaments(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  scope_level TEXT NOT NULL CHECK (scope_level IN ('product','color_variant')),
  claim_key TEXT NOT NULL CHECK (length(trim(claim_key)) > 0),
  value TEXT NOT NULL,
  unit TEXT,
  scope TEXT NOT NULL DEFAULT '{}',
  source_location TEXT,
  authority TEXT NOT NULL DEFAULT 'unknown',
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (review_status IN ('pending','approved','rejected')),
  notes TEXT,
  fingerprint TEXT NOT NULL CHECK (length(fingerprint) = 64),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (
    (scope_level = 'product' AND filament_id IS NULL) OR
    (scope_level = 'color_variant' AND filament_id IS NOT NULL)
  ),
  UNIQUE(owner_id, fingerprint)
);
CREATE INDEX claims_product_idx ON claims(product_id);
CREATE INDEX claims_filament_idx ON claims(filament_id);

-- 厂家预设是参数证据，不等同于本机校准；内部from=User也会原样保留。
CREATE TABLE preset_evaluations (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  product_id TEXT NOT NULL REFERENCES material_products(id) ON DELETE CASCADE,
  filament_id TEXT REFERENCES filaments(id) ON DELETE CASCADE,
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  scope_level TEXT NOT NULL CHECK (scope_level IN ('product','color_variant')),
  profile_name TEXT NOT NULL,
  target_printer TEXT NOT NULL,
  nozzle_mm REAL NOT NULL CHECK (nozzle_mm > 0),
  authority TEXT NOT NULL
    CHECK (authority IN ('bambu_system','manufacturer_profile','user_profile')),
  provenance TEXT NOT NULL,
  internal_origin TEXT,
  settings TEXT NOT NULL,
  warnings TEXT NOT NULL DEFAULT '[]',
  review_status TEXT NOT NULL DEFAULT 'pending'
    CHECK (review_status IN ('pending','approved','rejected')),
  fingerprint TEXT NOT NULL CHECK (length(fingerprint) = 64),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  CHECK (
    (scope_level = 'product' AND filament_id IS NULL) OR
    (scope_level = 'color_variant' AND filament_id IS NOT NULL)
  ),
  UNIQUE(owner_id, fingerprint)
);
CREATE INDEX preset_evaluations_product_idx ON preset_evaluations(product_id);
CREATE INDEX preset_evaluations_filament_idx ON preset_evaluations(filament_id);

CREATE TABLE profile_builds (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  filament_id TEXT NOT NULL REFERENCES filaments(id) ON DELETE CASCADE,
  target_printer TEXT NOT NULL,
  nozzle_mm REAL NOT NULL CHECK (nozzle_mm > 0),
  baseline_name TEXT NOT NULL,
  baseline_sha256 TEXT,
  generator_version TEXT NOT NULL,
  source_snapshot_hash TEXT NOT NULL,
  settings TEXT,
  diff TEXT NOT NULL DEFAULT '[]',
  status TEXT NOT NULL
    CHECK (status IN ('official_profile_available','draft_needs_calibration','slice_validated','print_calibrated','rejected')),
  validation TEXT NOT NULL DEFAULT '{}',
  artifact_paths TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE(owner_id, filament_id, target_printer, nozzle_mm, source_snapshot_hash, generator_version)
);
CREATE INDEX profile_builds_filament_idx ON profile_builds(filament_id);

-- 颜色、批次、机器、喷嘴和环境共同决定实测；不得回写厂家事实。
CREATE TABLE calibration_runs (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  filament_id TEXT NOT NULL REFERENCES filaments(id) ON DELETE CASCADE,
  profile_build_id TEXT REFERENCES profile_builds(id) ON DELETE SET NULL,
  machine TEXT NOT NULL,
  nozzle_mm REAL NOT NULL CHECK (nozzle_mm > 0),
  hotend TEXT,
  plate TEXT,
  lot TEXT,
  drying TEXT NOT NULL DEFAULT '{}',
  environment TEXT NOT NULL DEFAULT '{}',
  test_type TEXT NOT NULL,
  result TEXT NOT NULL,
  artifact_path TEXT,
  fingerprint TEXT NOT NULL CHECK (length(fingerprint) = 64),
  status TEXT NOT NULL DEFAULT 'recorded'
    CHECK (status IN ('recorded','accepted','rejected')),
  created_at TEXT NOT NULL,
  UNIQUE(owner_id, fingerprint)
);
CREATE INDEX calibration_runs_filament_idx ON calibration_runs(filament_id);

CREATE TABLE inventory_movements (
  id TEXT PRIMARY KEY,
  owner_id TEXT NOT NULL,
  filament_id TEXT NOT NULL REFERENCES filaments(id) ON DELETE CASCADE,
  movement_type TEXT NOT NULL
    CHECK (movement_type IN ('purchase','usage','count','correction','undo')),
  delta INTEGER NOT NULL CHECK (delta <> 0),
  before_spools INTEGER NOT NULL CHECK (before_spools >= 0),
  after_spools INTEGER NOT NULL CHECK (after_spools >= 0),
  note TEXT,
  reverses_movement_id TEXT REFERENCES inventory_movements(id) ON DELETE RESTRICT,
  created_at TEXT NOT NULL,
  CHECK (after_spools = before_spools + delta),
  CHECK (
    (movement_type = 'undo' AND reverses_movement_id IS NOT NULL) OR
    (movement_type <> 'undo' AND reverses_movement_id IS NULL)
  ),
  UNIQUE(owner_id, reverses_movement_id)
);
CREATE INDEX inventory_movements_created_idx ON inventory_movements(created_at DESC);
CREATE INDEX inventory_movements_filament_created_idx
  ON inventory_movements(filament_id, created_at DESC);
