from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tarfile
import hashlib
import inspect
import tempfile
import threading
import re
import mimetypes
from contextlib import closing, contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator
from uuid import UUID, uuid4

from .errors import DatabaseError, InputError
from .staging import load_manifest
from .material_domain import (
    FILAMENT_OPTIONAL_TEXT_FIELDS,
    FILAMENT_REQUIRED_TEXT_FIELDS,
    FILAMENT_STATUSES,
    INVENTORY_MOVEMENT_TYPES,
    clean_filament_text as _clean_filament_text,
    clean_optional_inventory_text as _clean_optional_inventory_text,
    classify_color_family as _classify_color_family,
    dashboard_filament as _dashboard_filament,
    inventory_summary as _inventory_summary,
    readiness_summary as _readiness_summary,
)

TABLES = (
    "material_products",
    "filaments",
    "sources",
    "claims",
    "preset_evaluations",
    "profile_builds",
    "calibration_runs",
    "inventory_movements",
)
JSON_COLUMNS = {
    "sources": {"metadata"},
    "claims": {"value", "scope"},
    "profile_builds": {"settings", "diff", "validation", "artifact_paths"},
    "calibration_runs": {"drying", "environment", "result"},
    "preset_evaluations": {"settings", "warnings"},
}
SOURCE_KINDS = {
    "manufacturer",
    "seller",
    "customer_service",
    "official_profile",
    "user_note",
}
SOURCE_DECISIONS = {
    "undecided",
    "use_default_profile",
    "reference_only",
    "needs_validation",
}
MAX_EVIDENCE_BYTES = 8 * 1024 * 1024


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


@dataclass(frozen=True)
class LocalStoreConfig:
    database_path: Path
    files_root: Path
    migrations_root: Path

    @classmethod
    def from_environment(cls) -> "LocalStoreConfig":
        package_root = Path(__file__).resolve().parents[2]
        data_root = Path(
            os.environ.get("PRINTPILOT_DATA_DIR", package_root / "data")
        ).expanduser().resolve()
        database_path = Path(
            os.environ.get("PRINTPILOT_DATABASE_PATH", data_root / "material-lab.sqlite3")
        ).expanduser().resolve()
        files_root = Path(
            os.environ.get("PRINTPILOT_FILES_ROOT", data_root / "files")
        ).expanduser().resolve()
        migrations_root = Path(__file__).with_name("sqlite_migrations")
        return cls(database_path, files_root, migrations_root)


class LocalStore:
    def __init__(self, config: LocalStoreConfig | None = None) -> None:
        self.config = config or LocalStoreConfig.from_environment()

    def initialize(self, owner_id: str | None = None) -> str:
        self.config.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.config.files_root.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
            )
            applied = {
                row[0]
                for row in connection.execute("SELECT version FROM schema_migrations")
            }
            for migration in sorted(self.config.migrations_root.glob("*.sql")):
                if migration.stem in applied:
                    continue
                connection.executescript(migration.read_text(encoding="utf-8"))
                connection.execute(
                    "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                    (migration.stem, _now()),
                )
            row = connection.execute(
                "SELECT value FROM app_metadata WHERE key='owner_id'"
            ).fetchone()
            selected_owner = owner_id or (row[0] if row else str(uuid4()))
            UUID(selected_owner)
            connection.execute(
                "INSERT INTO app_metadata(key,value) VALUES('owner_id',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (selected_owner,),
            )
            connection.commit()
        return selected_owner

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(
                self.config.database_path, timeout=10, isolation_level=None
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")
            connection.execute("PRAGMA synchronous=NORMAL")
            connection.execute("PRAGMA busy_timeout=10000")
            yield connection
        except sqlite3.Error as exc:
            raise DatabaseError("SQLite操作失败，请检查磁盘空间、文件权限和数据库完整性。") from exc
        finally:
            if connection is not None:
                connection.close()

    def owner_id(self, connection: sqlite3.Connection | None = None) -> str:
        if not self.config.database_path.exists():
            return self.initialize()
        if connection is not None:
            row = connection.execute(
                "SELECT value FROM app_metadata WHERE key='owner_id'"
            ).fetchone()
        else:
            with self.connect() as current:
                row = current.execute(
                    "SELECT value FROM app_metadata WHERE key='owner_id'"
                ).fetchone()
        if not row:
            raise DatabaseError("本地数据库缺少owner_id元数据。")
        return str(row[0])

    @staticmethod
    def _decode(table: str, row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        for column in JSON_COLUMNS.get(table, set()):
            value = result.get(column)
            if value is not None and isinstance(value, str):
                result[column] = json.loads(value)
        return result

    @staticmethod
    def _encode(table: str, row: dict[str, Any]) -> dict[str, Any]:
        result = dict(row)
        for column in JSON_COLUMNS.get(table, set()):
            value = result.get(column)
            if value is not None and not isinstance(value, str):
                result[column] = json.dumps(value, ensure_ascii=False, sort_keys=True)
        return result

    def _one_filament(
        self, connection: sqlite3.Connection, filament_id: str
    ) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM filament_inventory_view WHERE id=?", (filament_id,)
        ).fetchone()
        if not row:
            raise InputError("没有找到目标耗材。")
        return self._decode("filaments", row)

    def _one_product(
        self, connection: sqlite3.Connection, product_id: str
    ) -> dict[str, Any]:
        row = connection.execute(
            "SELECT * FROM material_products WHERE id=?", (product_id,)
        ).fetchone()
        if not row:
            raise InputError("没有找到目标耗材产品。")
        return self._decode("material_products", row)

    @staticmethod
    def _public_source(source: dict[str, Any]) -> dict[str, Any]:
        public = {
            key: value
            for key, value in source.items()
            if key not in {"storage_path", "extracted_text_path"}
        }
        public["file_url"] = f"/api/evidence/{source['id']}/file"
        return public

    def _ensure_product_for_filament(
        self, connection: sqlite3.Connection, filament: dict[str, Any]
    ) -> str:
        owner = str(filament["owner_id"])
        row = connection.execute(
            """
            SELECT id FROM material_products
            WHERE owner_id=? AND lower(brand)=lower(?)
              AND lower(product_line)=lower(?) AND lower(material_type)=lower(?)
              AND lower(coalesce(formulation,''))=lower(coalesce(?,''))
              AND diameter_mm=? AND lower(region)=lower(?)
            """,
            (
                owner,
                filament["brand"],
                filament["product_line"],
                filament["material_type"],
                filament.get("variant"),
                filament["diameter_mm"],
                filament["region"],
            ),
        ).fetchone()
        if row:
            product_id = str(row["id"])
            connection.execute(
                """
                UPDATE material_products
                SET manufacturer=coalesce(?,manufacturer), seller=coalesce(?,seller),
                    status=?, updated_at=?
                WHERE id=?
                """,
                (
                    filament.get("manufacturer"),
                    filament.get("seller"),
                    filament["status"],
                    filament["updated_at"],
                    product_id,
                ),
            )
        else:
            product_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO material_products(
                  id,owner_id,brand,manufacturer,seller,product_line,material_type,
                  formulation,diameter_mm,region,status,created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    product_id,
                    owner,
                    filament["brand"],
                    filament.get("manufacturer"),
                    filament.get("seller"),
                    filament["product_line"],
                    filament["material_type"],
                    filament.get("variant"),
                    filament["diameter_mm"],
                    filament["region"],
                    filament["status"],
                    filament["created_at"],
                    filament["updated_at"],
                ),
            )
        return product_id

    def list_inventory(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = [
                _inventory_summary(self._decode("filaments", row))
                for row in connection.execute("SELECT * FROM filament_inventory_view")
            ]
        return sorted(
            rows,
            key=lambda row: (
                str(row.get("brand") or "").casefold(),
                str(row.get("product_line") or "").casefold(),
                str(row.get("color") or "").casefold(),
            ),
        )

    def list_dashboard_filaments(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = [self._decode("filaments", row) for row in connection.execute("SELECT * FROM filament_inventory_view")]
            profile_counts = {
                row[0]: (int(row[1]), set(json.loads(row[2])))
                for row in connection.execute(
                    "SELECT filament_id,count(*),json_group_array(status) FROM profile_builds GROUP BY filament_id"
                )
            }
            calibration_counts = {
                row[0]: (int(row[1]), int(row[2]))
                for row in connection.execute(
                    "SELECT filament_id,count(*),sum(status='accepted') FROM calibration_runs GROUP BY filament_id"
                )
            }
            claims = [self._decode("claims", row) for row in connection.execute("SELECT * FROM claims")]
            preset_counts = {
                (str(row[0]), str(row[1]) if row[1] else None): int(row[2])
                for row in connection.execute(
                    "SELECT product_id,filament_id,count(*) FROM preset_evaluations GROUP BY product_id,filament_id"
                )
            }
            source_counts = {
                (str(row[0]), str(row[1]) if row[1] else None): int(row[2])
                for row in connection.execute(
                    "SELECT product_id,filament_id,count(*) FROM sources GROUP BY product_id,filament_id"
                )
            }
        claims_by_filament: dict[str, list[dict[str, Any]]] = {}
        claims_by_product: dict[str, list[dict[str, Any]]] = {}
        for claim in claims:
            if claim.get("scope_level") == "product":
                claims_by_product.setdefault(str(claim["product_id"]), []).append(claim)
            elif claim.get("filament_id"):
                claims_by_filament.setdefault(str(claim["filament_id"]), []).append(claim)
        records = []
        for row in rows:
            filament_id = str(row["id"])
            product_id = str(row.get("product_id") or "")
            profile_count, statuses = profile_counts.get(filament_id, (0, set()))
            calibration_count, accepted = calibration_counts.get(filament_id, (0, 0))
            effective_claims = [
                *claims_by_product.get(product_id, []),
                *claims_by_filament.get(filament_id, []),
            ]
            inherited_source_count = source_counts.get((product_id, None), 0) + source_counts.get(
                (product_id, filament_id), 0
            )
            evaluated_presets = preset_counts.get((product_id, None), 0) + preset_counts.get(
                (product_id, filament_id), 0
            )
            profiles = [{"status": status} for status in statuses]
            calibrations = ([{"status": "accepted"}] if accepted else []) + [
                {"status": "recorded"}
            ] * max(calibration_count - accepted, 0)
            records.append(
                {
                    **_dashboard_filament(row),
                    **_readiness_summary(
                        row, profiles, calibrations, effective_claims
                    ),
                    "profile_count": profile_count + evaluated_presets,
                    "calibration_count": calibration_count,
                    "source_count": inherited_source_count,
                    "claim_count": len(effective_claims),
                }
            )
        return sorted(records, key=lambda item: (str(item.get("brand") or "").casefold(), str(item.get("product_line") or "").casefold(), str(item.get("color") or "").casefold()))

    def list_products(self) -> list[dict[str, Any]]:
        variants = self.list_dashboard_filaments()
        grouped: dict[str, list[dict[str, Any]]] = {}
        with self.connect() as connection:
            products = {
                str(row["id"]): self._decode("material_products", row)
                for row in connection.execute("SELECT * FROM material_products")
            }
            preset_counts = {
                str(row[0]): (int(row[1]), int(row[2]))
                for row in connection.execute(
                    """
                    SELECT product_id,count(*),sum(authority='manufacturer_profile')
                    FROM preset_evaluations GROUP BY product_id
                    """
                )
            }
            product_sources = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT product_id,count(*) FROM sources GROUP BY product_id"
                )
            }
            product_claim_counts = {
                str(row[0]): int(row[1])
                for row in connection.execute(
                    "SELECT product_id,count(*) FROM claims WHERE scope_level='product' GROUP BY product_id"
                )
            }
        for variant in variants:
            product_id = str(variant.get("product_id") or "")
            if product_id:
                grouped.setdefault(product_id, []).append(variant)
        result = []
        for product_id, product in products.items():
            colors = grouped.get(product_id, [])
            source_count = product_sources.get(product_id, 0)
            claim_count = product_claim_counts.get(product_id, 0)
            preset_count, manufacturer_presets = preset_counts.get(product_id, (0, 0))
            result.append(
                {
                    "product_id": product_id,
                    "brand": product.get("brand"),
                    "manufacturer": product.get("manufacturer"),
                    "seller": product.get("seller"),
                    "product_line": product.get("product_line"),
                    "material_type": product.get("material_type"),
                    "formulation": product.get("formulation"),
                    "diameter_mm": product.get("diameter_mm"),
                    "region": product.get("region"),
                    "status": product.get("status"),
                    "color_count": len(colors),
                    "stock_spools": sum(int(item.get("stock_spools") or 0) for item in colors),
                    "opened_spool_count": sum(int(item.get("opened_remaining_percent") or 0) > 0 for item in colors),
                    "stock_equivalent": round(sum(float(item.get("stock_equivalent") or 0) for item in colors), 2),
                    "source_count": source_count,
                    "claim_count": claim_count,
                    "preset_count": preset_count,
                    "manufacturer_preset_count": manufacturer_presets,
                    "colors": colors,
                }
            )
        return sorted(
            result,
            key=lambda item: (
                str(item.get("brand") or "").casefold(),
                str(item.get("product_line") or "").casefold(),
                str(item.get("formulation") or "").casefold(),
            ),
        )

    def get_product_detail(self, product_id: str) -> dict[str, Any]:
        try:
            UUID(product_id)
        except ValueError as exc:
            raise InputError("product_id必须是有效UUID。") from exc
        with self.connect() as connection:
            product = self._one_product(connection, product_id)
            filament_rows = [
                self._decode("filaments", row)
                for row in connection.execute(
                    "SELECT * FROM filament_inventory_view WHERE product_id=? ORDER BY color", (product_id,)
                )
            ]
            claims = [
                self._decode("claims", row)
                for row in connection.execute(
                    "SELECT * FROM claims WHERE product_id=? ORDER BY created_at DESC",
                    (product_id,),
                )
            ]
            presets = [
                self._decode("preset_evaluations", row)
                for row in connection.execute(
                    "SELECT * FROM preset_evaluations WHERE product_id=? ORDER BY updated_at DESC",
                    (product_id,),
                )
            ]
            source_ids = {
                str(row["id"])
                for row in connection.execute(
                    "SELECT id FROM sources WHERE product_id=?", (product_id,)
                )
            }
            source_ids.update(str(row["source_id"]) for row in presets if row.get("source_id"))
            sources = [
                self._public_source(self._decode("sources", row))
                for row in connection.execute("SELECT * FROM sources")
                if str(row["id"]) in source_ids
            ]
        source_by_id = {str(row["id"]): row for row in sources}
        dashboard_by_id = {
            str(item["filament_id"]): item for item in self.list_dashboard_filaments()
        }
        variants = [dashboard_by_id[str(row["id"])] for row in filament_rows]
        product_claims = [item for item in claims if item["scope_level"] == "product"]
        variant_claims = [item for item in claims if item["scope_level"] == "color_variant"]
        return {
            "product": product,
            "colors": variants,
            "product_claims": [
                {**item, "source": source_by_id.get(str(item["source_id"]))}
                for item in product_claims
            ],
            "color_claims": [
                {**item, "source": source_by_id.get(str(item["source_id"]))}
                for item in variant_claims
            ],
            "presets": [
                {**item, "source": source_by_id.get(str(item.get("source_id")))}
                for item in presets
            ],
            "sources": sources,
            "summary": {
                "color_count": len(variants),
                "stock_spools": sum(int(item.get("stock_spools") or 0) for item in variants),
                "stock_equivalent": round(sum(float(item.get("stock_equivalent") or 0) for item in variants), 2),
                "product_claim_count": len(product_claims),
                "color_claim_count": len(variant_claims),
                "preset_count": len(presets),
            },
        }

    def get_filament_detail(self, filament_id: str) -> dict[str, Any]:
        try:
            UUID(filament_id)
        except ValueError as exc:
            raise InputError("filament_id必须是有效UUID。") from exc
        with self.connect() as connection:
            filament = self._one_filament(connection, filament_id)
            product_id = self._ensure_product_for_filament(connection, filament)
            profiles = [self._decode("profile_builds", row) for row in connection.execute("SELECT * FROM profile_builds WHERE filament_id=? ORDER BY updated_at DESC", (filament_id,))]
            calibrations = [self._decode("calibration_runs", row) for row in connection.execute("SELECT * FROM calibration_runs WHERE filament_id=? ORDER BY created_at DESC", (filament_id,))]
            claims = [
                self._decode("claims", row)
                for row in connection.execute(
                    "SELECT * FROM claims WHERE product_id=? AND (scope_level='product' OR filament_id=?) ORDER BY scope_level,created_at DESC",
                    (product_id, filament_id),
                )
            ]
            source_ids = {
                str(row["id"])
                for row in connection.execute(
                    "SELECT id FROM sources WHERE product_id=? AND (scope_level='product' OR filament_id=?)",
                    (product_id, filament_id),
                )
            }
            sources = [self._decode("sources", row) for row in connection.execute("SELECT * FROM sources") if str(row["id"]) in source_ids]
            movements = [self._decode("inventory_movements", row) for row in connection.execute("SELECT * FROM inventory_movements WHERE filament_id=? ORDER BY created_at DESC LIMIT 50", (filament_id,))]
        public_source_by_id: dict[str, dict[str, Any]] = {}
        public_sources = []
        for source in sources:
            public = self._public_source(source)
            public_source_by_id[str(source["id"])] = public
            public_sources.append(public)
        return {
            "filament": {**_dashboard_filament(filament), **_readiness_summary(filament, profiles, calibrations, claims)},
            "profiles": profiles,
            "calibrations": calibrations,
            "claims": [
                {**claim, "source": public_source_by_id.get(str(claim["source_id"]))}
                for claim in claims
            ],
            "sources": public_sources,
            "movements": movements,
        }

    @staticmethod
    def _safe_evidence_name(filename: str | None, media_type: str | None) -> str:
        candidate = Path(str(filename or "evidence.bin")).name.strip()
        candidate = re.sub(r"[^A-Za-z0-9._-]+", "_", candidate)[:120].strip(".")
        if candidate:
            return candidate
        extension = mimetypes.guess_extension(media_type or "") or ".bin"
        return f"evidence{extension}"

    def add_evidence(
        self,
        filament_id: str,
        source: dict[str, Any],
        claims: list[dict[str, Any]],
        file_bytes: bytes | None,
        filename: str | None,
        media_type: str | None,
        approved: bool,
    ) -> dict[str, Any]:
        if not approved:
            raise InputError("厂家资料写入必须显式确认。")
        try:
            UUID(filament_id)
        except ValueError as exc:
            raise InputError("filament_id必须是有效UUID。") from exc
        kind = source.get("kind", "seller")
        if kind not in SOURCE_KINDS:
            raise InputError("资料来源类型无效。")
        decision = source.get("user_decision", "undecided")
        if decision not in SOURCE_DECISIONS:
            raise InputError("资料采用决定无效。")
        scope_level = str(source.get("scope_level") or "product")
        if scope_level not in {"product", "color_variant"}:
            raise InputError("资料适用范围必须是整个产品或当前颜色。")
        title = _clean_optional_inventory_text(source.get("title"), "title", 200)
        origin = _clean_optional_inventory_text(source.get("origin"), "origin", 1000)
        organization = _clean_optional_inventory_text(
            source.get("source_organization"), "source_organization", 200
        )
        region = _clean_optional_inventory_text(source.get("region"), "region", 50)
        version = _clean_optional_inventory_text(
            source.get("document_version"), "document_version", 100
        )
        notes = _clean_optional_inventory_text(source.get("notes"), "notes", 2000)
        quote = _clean_optional_inventory_text(source.get("quote"), "quote", 4000)
        if file_bytes is not None and len(file_bytes) > MAX_EVIDENCE_BYTES:
            raise InputError("单份厂家资料不能超过8MB。")
        if not isinstance(claims, list) or len(claims) > 50:
            raise InputError("参数记录必须是最多50项的数组。")
        normalized_claims: list[dict[str, Any]] = []
        for item in claims:
            if not isinstance(item, dict):
                raise InputError("每条参数记录必须是对象。")
            key = item.get("key")
            if not isinstance(key, str) or not key.strip() or len(key.strip()) > 100:
                raise InputError("参数名称不能为空且不能超过100个字符。")
            if "value" not in item or item["value"] is None:
                raise InputError(f"参数“{key}”缺少值。")
            value = item["value"]
            if isinstance(value, str) and len(value.strip()) > 2000:
                raise InputError(f"参数“{key}”不能超过2000个字符。")
            try:
                json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                raise InputError(f"参数“{key}”的值无法保存。") from exc
            unit = _clean_optional_inventory_text(item.get("unit"), "unit", 50)
            claim_notes = _clean_optional_inventory_text(item.get("notes"), "claim_notes", 1000)
            review_status = item.get("review_status", "pending")
            if review_status not in {"pending", "approved", "rejected"}:
                raise InputError("参数审核状态无效。")
            normalized_claims.append(
                {
                    "key": key.strip(),
                    "value": value,
                    "unit": unit,
                    "scope": item.get("scope") if isinstance(item.get("scope"), dict) else {},
                    "notes": claim_notes,
                    "review_status": review_status,
                }
            )
        if quote:
            normalized_claims.insert(
                0,
                {
                    "key": "customer_quote",
                    "value": quote,
                    "unit": None,
                    "scope": {},
                    "notes": "供应商或客服原话；不等同于结构化打印参数。",
                    "review_status": "approved",
                },
            )
        if not normalized_claims:
            normalized_claims.append(
                {
                    "key": "source_note",
                    "value": title or "已上传厂家资料",
                    "unit": None,
                    "scope": {},
                    "notes": None,
                    "review_status": "pending",
                }
            )
        source_payload = {
            "kind": kind,
            "title": title,
            "origin": origin,
            "source_organization": organization,
            "region": region,
            "document_version": version,
            "user_decision": decision,
            "notes": notes,
            "claims": normalized_claims,
            "filename": filename,
            "media_type": media_type,
        }
        evidence_bytes = file_bytes or json.dumps(
            source_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        source_hash = hashlib.sha256(evidence_bytes).hexdigest()
        safe_name = self._safe_evidence_name(filename, media_type)
        relative = Path("evidence") / source_hash / safe_name
        destination = self.config.files_root / relative
        now = _now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            filament = self._one_filament(connection, filament_id)
            product_id = self._ensure_product_for_filament(connection, filament)
            owner = self.owner_id(connection)
            scoped_filament_id = filament_id if scope_level == "color_variant" else None
            if scoped_filament_id:
                existing = connection.execute(
                    "SELECT * FROM sources WHERE owner_id=? AND product_id=? AND filament_id=? AND sha256=?",
                    (owner, product_id, scoped_filament_id, source_hash),
                ).fetchone()
            else:
                existing = connection.execute(
                    "SELECT * FROM sources WHERE owner_id=? AND product_id=? AND filament_id IS NULL AND sha256=?",
                    (owner, product_id, source_hash),
                ).fetchone()
            if existing:
                source_id = str(existing["id"])
                relative = Path(str(existing["storage_path"]))
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(evidence_bytes)
                source_id = str(uuid4())
                metadata = {
                    "user_decision": decision,
                    "notes": notes,
                    "filename": safe_name,
                    "uploaded_from_dashboard": True,
                }
                connection.execute(
                    "INSERT INTO sources(id,owner_id,product_id,filament_id,scope_level,kind,title,origin,source_organization,region,document_version,retrieved_at,media_type,sha256,storage_path,extracted_text_path,metadata,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        source_id,
                        owner,
                        product_id,
                        scoped_filament_id,
                        scope_level,
                        kind,
                        title or safe_name,
                        origin,
                        organization,
                        region,
                        version,
                        now,
                        media_type or mimetypes.guess_type(safe_name)[0],
                        source_hash,
                        relative.as_posix(),
                        None,
                        json.dumps(metadata, ensure_ascii=False),
                        now,
                    ),
                )
            inserted = 0
            for claim in normalized_claims:
                fingerprint = hashlib.sha256(
                    json.dumps(
                        {
                            "product_id": product_id,
                            "filament_id": scoped_filament_id,
                            "scope_level": scope_level,
                            "source_id": source_id,
                            "key": claim["key"],
                            "value": claim["value"],
                            "unit": claim["unit"],
                            "scope": claim["scope"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if connection.execute(
                    "SELECT 1 FROM claims WHERE owner_id=? AND fingerprint=?",
                    (owner, fingerprint),
                ).fetchone():
                    continue
                connection.execute(
                    "INSERT INTO claims(id,owner_id,product_id,filament_id,source_id,scope_level,claim_key,value,unit,scope,source_location,authority,review_status,notes,fingerprint,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid4()),
                        owner,
                        product_id,
                        scoped_filament_id,
                        source_id,
                        scope_level,
                        claim["key"],
                        json.dumps(claim["value"], ensure_ascii=False),
                        claim["unit"],
                        json.dumps(claim["scope"], ensure_ascii=False),
                        None,
                        kind,
                        claim["review_status"],
                        claim["notes"],
                        fingerprint,
                        now,
                        now,
                    ),
                )
                inserted += 1
            connection.commit()
        return {
            "source_id": source_id,
            "sha256": source_hash,
            "inserted_claims": inserted,
            "deduplicated_source": bool(existing),
            "scope_level": scope_level,
            "file_url": f"/api/evidence/{source_id}/file",
        }

    def add_product_inbox_evidence(
        self,
        product_id: str,
        source: dict[str, Any],
        file_bytes: bytes,
        filename: str,
        media_type: str,
        approved: bool,
    ) -> dict[str, Any]:
        """Archive an unprocessed product image without creating claims."""

        if not approved:
            raise InputError("产品资料写入必须显式确认。")
        try:
            UUID(product_id)
        except ValueError as exc:
            raise InputError("product_id必须是有效UUID。") from exc
        kind = str(source.get("kind") or "seller")
        if kind not in SOURCE_KINDS:
            raise InputError("资料来源类型无效。")
        title = _clean_optional_inventory_text(source.get("title"), "title", 200)
        origin = _clean_optional_inventory_text(source.get("origin"), "origin", 1000)
        organization = _clean_optional_inventory_text(
            source.get("source_organization"), "source_organization", 200
        )
        region = _clean_optional_inventory_text(source.get("region"), "region", 50)
        notes = _clean_optional_inventory_text(source.get("notes"), "notes", 2000)
        if not file_bytes:
            raise InputError("产品资料图片不能为空。")
        if len(file_bytes) > MAX_EVIDENCE_BYTES:
            raise InputError("单张产品资料图片不能超过8MB。")

        source_hash = hashlib.sha256(file_bytes).hexdigest()
        safe_name = self._safe_evidence_name(filename, media_type)
        relative = Path("evidence") / source_hash / safe_name
        destination = self.config.files_root / relative
        now = _now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._one_product(connection, product_id)
            owner = self.owner_id(connection)
            existing = connection.execute(
                "SELECT * FROM sources WHERE owner_id=? AND product_id=? AND filament_id IS NULL AND sha256=?",
                (owner, product_id, source_hash),
            ).fetchone()
            if existing:
                source_id = str(existing["id"])
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(file_bytes)
                source_id = str(uuid4())
                metadata = {
                    "processing_status": "pending_manual_review",
                    "uploaded_from": "product_inbox",
                    "filename": safe_name,
                    "notes": notes,
                }
                connection.execute(
                    "INSERT INTO sources(id,owner_id,product_id,filament_id,scope_level,kind,title,origin,source_organization,region,document_version,retrieved_at,media_type,sha256,storage_path,extracted_text_path,metadata,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        source_id,
                        owner,
                        product_id,
                        None,
                        "product",
                        kind,
                        title or safe_name,
                        origin,
                        organization,
                        region,
                        None,
                        now,
                        media_type,
                        source_hash,
                        relative.as_posix(),
                        None,
                        json.dumps(metadata, ensure_ascii=False),
                        now,
                    ),
                )
            connection.commit()
        return {
            "source_id": source_id,
            "sha256": source_hash,
            "inserted_claims": 0,
            "deduplicated_source": bool(existing),
            "scope_level": "product",
            "processing_status": "pending_manual_review",
            "file_url": f"/api/evidence/{source_id}/file",
        }

    def process_product_inbox_evidence(
        self,
        source_id: str,
        claims: list[dict[str, Any]],
        extracted_text: str | None,
        approved: bool,
    ) -> dict[str, Any]:
        """Attach verified product claims to an already archived inbox source."""

        if not approved:
            raise InputError("产品资料整理必须显式确认。")
        try:
            UUID(source_id)
        except ValueError as exc:
            raise InputError("source_id必须是有效UUID。") from exc
        if not isinstance(claims, list) or not claims:
            raise InputError("至少需要一条已核对的参数记录。")

        normalized: list[dict[str, Any]] = []
        for item in claims:
            if not isinstance(item, dict):
                raise InputError("每条参数记录必须是对象。")
            key = str(item.get("key") or "").strip()
            if not key or len(key) > 100:
                raise InputError("参数名称不能为空且不能超过100个字符。")
            if "value" not in item or item["value"] is None:
                raise InputError(f"参数“{key}”缺少值。")
            value = item["value"]
            try:
                json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError) as exc:
                raise InputError(f"参数“{key}”的值无法保存。") from exc
            review_status = str(item.get("review_status") or "approved")
            if review_status not in {"pending", "approved", "rejected"}:
                raise InputError("参数审核状态无效。")
            normalized.append(
                {
                    "key": key,
                    "value": value,
                    "unit": _clean_optional_inventory_text(item.get("unit"), "unit", 50),
                    "scope": item.get("scope") if isinstance(item.get("scope"), dict) else {},
                    "source_location": _clean_optional_inventory_text(
                        item.get("source_location"), "source_location", 500
                    ),
                    "notes": _clean_optional_inventory_text(item.get("notes"), "claim_notes", 1000),
                    "review_status": review_status,
                }
            )

        now = _now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = self.owner_id(connection)
            source = connection.execute(
                "SELECT * FROM sources WHERE id=? AND owner_id=?",
                (source_id, owner),
            ).fetchone()
            if not source:
                raise InputError("没有找到待整理的产品资料。")
            if str(source["scope_level"]) != "product" or source["filament_id"] is not None:
                raise InputError("该资料不是产品级资料，不能用产品收件箱流程整理。")
            metadata = json.loads(str(source["metadata"] or "{}"))
            inserted = 0
            for claim in normalized:
                fingerprint = hashlib.sha256(
                    json.dumps(
                        {
                            "product_id": str(source["product_id"]),
                            "filament_id": None,
                            "scope_level": "product",
                            "source_id": source_id,
                            "key": claim["key"],
                            "value": claim["value"],
                            "unit": claim["unit"],
                            "scope": claim["scope"],
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if connection.execute(
                    "SELECT 1 FROM claims WHERE owner_id=? AND fingerprint=?",
                    (owner, fingerprint),
                ).fetchone():
                    continue
                connection.execute(
                    "INSERT INTO claims(id,owner_id,product_id,filament_id,source_id,scope_level,claim_key,value,unit,scope,source_location,authority,review_status,notes,fingerprint,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        str(uuid4()), owner, str(source["product_id"]), None, source_id,
                        "product", claim["key"], json.dumps(claim["value"], ensure_ascii=False),
                        claim["unit"], json.dumps(claim["scope"], ensure_ascii=False),
                        claim["source_location"], str(source["kind"]), claim["review_status"],
                        claim["notes"], fingerprint, now, now,
                    ),
                )
                inserted += 1

            extracted_relative: str | None = str(source["extracted_text_path"] or "") or None
            clean_text = (extracted_text or "").strip()
            if clean_text:
                source_relative = Path(str(source["storage_path"]))
                extracted_path = source_relative.parent / "extracted.txt"
                destination = (self.config.files_root / extracted_path).resolve()
                if not destination.is_relative_to(self.config.files_root):
                    raise InputError("资料文本保存路径无效。")
                destination.write_text(clean_text[:100000], encoding="utf-8")
                extracted_relative = extracted_path.as_posix()

            metadata.update(
                {
                    "processing_status": "processed",
                    "processed_at": now,
                    "processor": "manual_ai_assisted",
                    "extracted_claim_count": len(normalized),
                }
            )
            connection.execute(
                "UPDATE sources SET extracted_text_path=?, metadata=? WHERE id=? AND owner_id=?",
                (extracted_relative, json.dumps(metadata, ensure_ascii=False), source_id, owner),
            )
            connection.commit()
        return {
            "source_id": source_id,
            "inserted_claims": inserted,
            "processing_status": "processed",
            "extracted_text_path": extracted_relative,
        }

    def get_source_file(self, source_id: str) -> tuple[Path, str | None, str]:
        try:
            UUID(source_id)
        except ValueError as exc:
            raise InputError("source_id必须是有效UUID。") from exc
        with self.connect() as connection:
            owner = self.owner_id(connection)
            row = connection.execute(
                "SELECT storage_path,media_type,title FROM sources WHERE id=? AND owner_id=?",
                (source_id, owner),
            ).fetchone()
        if not row:
            raise InputError("没有找到厂家资料。")
        path = (self.config.files_root / str(row["storage_path"])).resolve()
        if not path.is_relative_to(self.config.files_root) or not path.is_file():
            raise InputError("厂家资料文件不存在。")
        return path, row["media_type"], str(row["title"] or path.name)

    def add_preset_evaluation(
        self,
        product_id: str,
        filament_id: str | None,
        evaluation: dict[str, Any],
        file_bytes: bytes,
        filename: str,
        approved: bool,
    ) -> dict[str, Any]:
        """Archive one parsed preset as manufacturer evidence and evaluation."""

        if not approved:
            raise InputError("厂家预设建档必须显式确认。")
        try:
            UUID(product_id)
            if filament_id:
                UUID(filament_id)
        except ValueError as exc:
            raise InputError("产品或颜色库存ID无效。") from exc
        scope_level = str(evaluation.get("scope_level") or "")
        if scope_level not in {"product", "color_variant"}:
            raise InputError("预设作用域无效。")
        if scope_level == "color_variant" and not filament_id:
            raise InputError("颜色专用预设必须绑定一个颜色库存项。")
        if scope_level == "product" and filament_id:
            raise InputError("产品通用预设不能绑定颜色库存项。")
        authority = str(evaluation.get("authority") or "")
        if authority not in {"bambu_system", "manufacturer_profile", "user_profile"}:
            raise InputError("预设来源级别无效。")
        source_hash = hashlib.sha256(file_bytes).hexdigest()
        profile_fingerprint = hashlib.sha256(
            json.dumps(
                {
                    "product_id": product_id,
                    "filament_id": filament_id,
                    "source_sha256": source_hash,
                    "entry": evaluation.get("entry"),
                    "settings": evaluation.get("settings") or {},
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        safe_name = self._safe_evidence_name(filename, None)
        relative = Path("presets") / source_hash / safe_name
        now = _now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            self._one_product(connection, product_id)
            if filament_id:
                variant = self._one_filament(connection, filament_id)
                if str(variant["product_id"]) != product_id:
                    raise InputError("颜色库存项不属于目标产品。")
            owner = self.owner_id(connection)
            source = connection.execute(
                "SELECT id FROM sources WHERE owner_id=? AND product_id=? AND filament_id IS ? AND sha256=?",
                (owner, product_id, filament_id, source_hash),
            ).fetchone()
            if source:
                source_id = str(source["id"])
            else:
                destination = self.config.files_root / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    destination.write_bytes(file_bytes)
                source_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO sources(
                      id,owner_id,product_id,filament_id,scope_level,kind,title,
                      source_organization,region,retrieved_at,media_type,sha256,
                      storage_path,metadata,created_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        source_id,
                        owner,
                        product_id,
                        filament_id,
                        scope_level,
                        "official_profile",
                        str(evaluation.get("profile_name") or filename),
                        str(evaluation.get("vendor") or "") or None,
                        None,
                        now,
                        "application/zip" if filename.casefold().endswith(".bbsflmt") else "application/json",
                        source_hash,
                        relative.as_posix(),
                        json.dumps(
                            {
                                "provenance": evaluation.get("provenance"),
                                "internal_origin": evaluation.get("internal_origin"),
                                "source_filename": filename,
                            },
                            ensure_ascii=False,
                        ),
                        now,
                    ),
                )
            existing = connection.execute(
                "SELECT id FROM preset_evaluations WHERE owner_id=? AND fingerprint=?",
                (owner, profile_fingerprint),
            ).fetchone()
            if existing:
                connection.commit()
                return {
                    "preset_evaluation_id": str(existing["id"]),
                    "source_id": source_id,
                    "created": False,
                }
            evaluation_id = str(uuid4())
            connection.execute(
                """
                INSERT INTO preset_evaluations(
                  id,owner_id,product_id,filament_id,source_id,scope_level,
                  profile_name,target_printer,nozzle_mm,authority,provenance,
                  internal_origin,settings,warnings,review_status,fingerprint,
                  created_at,updated_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    evaluation_id,
                    owner,
                    product_id,
                    filament_id,
                    source_id,
                    scope_level,
                    evaluation["profile_name"],
                    evaluation["target_printer"],
                    float(evaluation["nozzle_mm"]),
                    authority,
                    str(evaluation.get("provenance") or "来源待核验"),
                    evaluation.get("internal_origin"),
                    json.dumps(evaluation.get("settings") or {}, ensure_ascii=False),
                    json.dumps(evaluation.get("warnings") or [], ensure_ascii=False),
                    "approved",
                    profile_fingerprint,
                    now,
                    now,
                ),
            )
            connection.commit()
        return {
            "preset_evaluation_id": evaluation_id,
            "source_id": source_id,
            "created": True,
        }

    def create_filament_record(self, fields: dict[str, Any], stock_spools: int, spool_weight_g: int, low_stock_threshold: int, target_stock_spools: int, storage_location: str | None, inventory_notes: str | None, approved: bool, opened_remaining_percent: int = 0) -> dict[str, Any]:
        if not approved:
            raise InputError("耗材档案写入必须显式传入--approved。")
        missing = sorted(field for field in FILAMENT_REQUIRED_TEXT_FIELDS if field not in fields)
        if missing:
            raise InputError(f"缺少必填字段：{', '.join(missing)}。")
        if not 0 <= stock_spools <= 10000 or not 1 <= spool_weight_g <= 100000:
            raise InputError("库存卷数或单卷净重超出允许范围。")
        if not 0 <= opened_remaining_percent <= 100:
            raise InputError("在用卷余量必须在0%到100%之间。")
        if low_stock_threshold < 0 or target_stock_spools < 0:
            raise InputError("库存阈值和目标库存不能小于0。")
        clean: dict[str, Any] = {field: _clean_filament_text(fields.get(field), field, required=True) for field in FILAMENT_REQUIRED_TEXT_FIELDS}
        clean.update({field: _clean_filament_text(fields.get(field), field, required=False) for field in FILAMENT_OPTIONAL_TEXT_FIELDS})
        clean["color_family"] = clean.get("color_family") or _classify_color_family(clean.get("color"))
        diameter = float(fields.get("diameter_mm", 1.75))
        if diameter not in {1.75, 2.85}:
            raise InputError("线径目前只支持1.75或2.85毫米。")
        status = fields.get("status", "reviewed")
        if status not in FILAMENT_STATUSES:
            raise InputError("档案状态无效。")
        generated_identity = False
        if not clean.get("sku") and not clean.get("barcode"):
            # SKU/条码是供应商身份，不应该阻塞用户先把截图建档。
            # 这里生成的是本地内部标识，绝不冒充厂家SKU；用户补充真实标识后可在编辑页覆盖。
            clean["sku"] = f"PP-AUTO-{uuid4().hex[:12].upper()}"
            generated_identity = True
        cleaned_notes = _clean_optional_inventory_text(inventory_notes, "inventory_notes", 1000)
        if generated_identity:
            marker = "系统自动生成内部标识，待补充商品SKU/条码。"
            cleaned_notes = f"{marker}{(' ' + cleaned_notes) if cleaned_notes else ''}"[:1000]
        filament_id, created_at = str(uuid4()), _now()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                owner = self.owner_id(connection)
                product_id = str(uuid4())
                connection.execute(
                    """
                    INSERT INTO material_products(
                      id,owner_id,brand,manufacturer,seller,product_line,material_type,
                      formulation,diameter_mm,region,status,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        product_id,
                        owner,
                        clean["brand"],
                        clean.get("manufacturer"),
                        clean.get("seller"),
                        clean["product_line"],
                        clean["material_type"],
                        clean.get("variant"),
                        diameter,
                        clean["region"],
                        status,
                        created_at,
                        created_at,
                    ),
                )
                product_row = connection.execute(
                    """
                    SELECT id FROM material_products
                    WHERE owner_id=? AND lower(brand)=lower(?)
                      AND lower(product_line)=lower(?) AND lower(material_type)=lower(?)
                      AND lower(coalesce(formulation,''))=lower(coalesce(?,''))
                      AND diameter_mm=? AND lower(region)=lower(?)
                    """,
                    (
                        owner,
                        clean["brand"],
                        clean["product_line"],
                        clean["material_type"],
                        clean.get("variant"),
                        diameter,
                        clean["region"],
                    ),
                ).fetchone()
                if not product_row:
                    raise DatabaseError("无法建立产品与颜色库存的关联。")
                product_id = str(product_row["id"])
                connection.execute(
                    "INSERT INTO filaments(id,owner_id,product_id,color,color_family,sku,barcode,stock_spools,opened_remaining_percent,spool_weight_g,low_stock_threshold,target_stock_spools,storage_location,inventory_notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (filament_id, owner, product_id, clean.get("color"), clean.get("color_family"), clean.get("sku"), clean.get("barcode"), 0, opened_remaining_percent, spool_weight_g, low_stock_threshold, target_stock_spools, _clean_optional_inventory_text(storage_location, "storage_location", 200), cleaned_notes, created_at, created_at),
                )
                if stock_spools:
                    self._apply_movement(connection, filament_id, stock_spools, "purchase", "新建耗材时录入初始库存")
                connection.commit()
                return _dashboard_filament(self._one_filament(connection, filament_id))
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise InputError("相同条码或同品牌、SKU和地区的耗材档案已经存在。") from exc

    def update_filament_record(self, filament_id: str, fields: dict[str, Any], approved: bool) -> dict[str, Any]:
        if not approved:
            raise InputError("耗材档案写入必须显式传入--approved。")
        allowed = FILAMENT_REQUIRED_TEXT_FIELDS | FILAMENT_OPTIONAL_TEXT_FIELDS | {"diameter_mm", "status"}
        unknown = set(fields) - allowed
        if unknown or not fields:
            raise InputError("没有允许保存的耗材字段。")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._one_filament(connection, filament_id)
            before = _dashboard_filament(current)
            clean: dict[str, Any] = {}
            for field in FILAMENT_REQUIRED_TEXT_FIELDS:
                if field in fields:
                    clean[field] = _clean_filament_text(fields[field], field, required=True)
            for field in FILAMENT_OPTIONAL_TEXT_FIELDS:
                if field in fields:
                    clean[field] = _clean_filament_text(fields[field], field, required=False)
            if "color" in fields and "color_family" not in fields:
                clean["color_family"] = _classify_color_family(clean.get("color"))
            elif "color_family" in clean and clean["color_family"] is None:
                clean["color_family"] = _classify_color_family(
                    clean.get("color", current.get("color"))
                )
            if "diameter_mm" in fields:
                diameter = float(fields["diameter_mm"])
                if diameter not in {1.75, 2.85}:
                    raise InputError("线径目前只支持1.75或2.85毫米。")
                clean["diameter_mm"] = diameter
            if "status" in fields:
                if fields["status"] not in FILAMENT_STATUSES:
                    raise InputError("档案状态无效。")
                clean["status"] = fields["status"]
            merged = {**current, **clean}
            if not merged.get("sku") and not merged.get("barcode"):
                raise InputError("SKU和条码至少需要保留一个。")
            updated_at = _now()
            product_identity_changed = bool(
                {"brand", "manufacturer", "seller", "product_line", "material_type", "variant", "diameter_mm", "region"}
                & set(clean)
            ) or "status" in clean
            filament_updates = {
                key: value
                for key, value in clean.items()
                if key in {"color", "color_family", "sku", "barcode"}
            }
            if product_identity_changed:
                merged["updated_at"] = updated_at
                filament_updates["product_id"] = self._ensure_product_for_filament(
                    connection, {**merged, "product_id": None}
                )
            filament_updates["updated_at"] = updated_at
            assignments = ",".join(f"{key}=?" for key in filament_updates)
            try:
                connection.execute(
                    f"UPDATE filaments SET {assignments} WHERE id=?",
                    (*filament_updates.values(), filament_id),
                )
                connection.commit()
            except sqlite3.IntegrityError as exc:
                connection.rollback()
                raise InputError("条码或同品牌、SKU和地区的档案已存在。") from exc
            return {"before": before, "after": _dashboard_filament(self._one_filament(connection, filament_id))}

    def _apply_movement(self, connection: sqlite3.Connection, filament_id: str, delta: int, movement_type: str, note: str | None, reverses: str | None = None) -> dict[str, Any]:
        current = self._one_filament(connection, filament_id)
        before, after = int(current["stock_spools"]), int(current["stock_spools"]) + delta
        if after < 0:
            raise InputError(f"库存不足：当前{before}卷，不能调整{delta:+d}卷。")
        movement_id, created_at = str(uuid4()), _now()
        connection.execute("UPDATE filaments SET stock_spools=?,updated_at=? WHERE id=?", (after, created_at, filament_id))
        connection.execute("INSERT INTO inventory_movements(id,owner_id,filament_id,movement_type,delta,before_spools,after_spools,note,reverses_movement_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)", (movement_id, current["owner_id"], filament_id, movement_type, delta, before, after, _clean_optional_inventory_text(note, "note", 500), reverses, created_at))
        return {"movement_id": movement_id, "filament_id": filament_id, "delta": delta, "before_spools": before, "after_spools": after, "movement_type": movement_type}

    def adjust_inventory(self, filament_id: str, delta: int, approved: bool, movement_type: str = "correction", note: str | None = None) -> dict[str, Any]:
        if not approved or delta == 0 or movement_type not in INVENTORY_MOVEMENT_TYPES:
            raise InputError("库存写入未确认、调整量为0或变动类型无效。")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._one_filament(connection, filament_id)
            movement = self._apply_movement(connection, filament_id, delta, movement_type, note)
            updated = self._one_filament(connection, filament_id)
            connection.commit()
        return {"movement": movement, "delta": delta, "before": _inventory_summary(current), "after": _inventory_summary(updated)}

    def set_inventory_details(self, filament_id: str, stock_spools: int, spool_weight_g: int | None, low_stock_threshold: int | None, target_stock_spools: int | None, storage_location: str | None, inventory_notes: str | None, movement_note: str | None, approved: bool, opened_remaining_percent: int | None = None) -> dict[str, Any]:
        if not approved or stock_spools < 0:
            raise InputError("库存盘点未确认或库存卷数无效。")
        if spool_weight_g is not None and spool_weight_g <= 0:
            raise InputError("单卷净重必须大于0克。")
        if low_stock_threshold is not None and low_stock_threshold < 0 or target_stock_spools is not None and target_stock_spools < 0:
            raise InputError("库存阈值不能小于0。")
        if opened_remaining_percent is not None and not 0 <= opened_remaining_percent <= 100:
            raise InputError("在用卷余量必须在0%到100%之间。")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            current = self._one_filament(connection, filament_id)
            before_summary = _inventory_summary(current)
            fields: dict[str, Any] = {"updated_at": _now()}
            if spool_weight_g is not None: fields["spool_weight_g"] = spool_weight_g
            if low_stock_threshold is not None: fields["low_stock_threshold"] = low_stock_threshold
            if target_stock_spools is not None: fields["target_stock_spools"] = target_stock_spools
            if opened_remaining_percent is not None: fields["opened_remaining_percent"] = opened_remaining_percent
            if storage_location is not None: fields["storage_location"] = _clean_optional_inventory_text(storage_location, "storage_location", 200)
            if inventory_notes is not None: fields["inventory_notes"] = _clean_optional_inventory_text(inventory_notes, "inventory_notes", 1000)
            connection.execute(f"UPDATE filaments SET {','.join(f'{key}=?' for key in fields)} WHERE id=?", (*fields.values(), filament_id))
            delta = stock_spools - int(current["stock_spools"])
            movement = self._apply_movement(connection, filament_id, delta, "count", movement_note) if delta else None
            updated = self._one_filament(connection, filament_id)
            connection.commit()
        return {"movement": movement, "before": before_summary, "after": _inventory_summary(updated)}

    def list_inventory_movements(self, filament_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
        if not 1 <= limit <= 200:
            raise InputError("库存历史条数必须在1到200之间。")
        query, params = "SELECT * FROM inventory_movements", []
        if filament_id:
            query, params = query + " WHERE filament_id=?", [filament_id]
        query += " ORDER BY created_at DESC LIMIT ?"
        with self.connect() as connection:
            return [self._decode("inventory_movements", row) for row in connection.execute(query, (*params, limit))]

    def import_inventory_rows(
        self, rows: list[dict[str, Any]], approved: bool
    ) -> dict[str, Any]:
        """Idempotently import product/color rows from a reviewed inventory matrix."""

        if not approved:
            raise InputError("库存表导入必须显式确认。")
        if not rows:
            raise InputError("库存表中没有可导入的在库耗材。")
        inserted = updated = unchanged = 0
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            owner = self.owner_id(connection)
            try:
                for raw in rows:
                    required = ("brand", "product_line", "material_type", "color", "sku")
                    if any(not str(raw.get(key) or "").strip() for key in required):
                        raise InputError("库存导入行缺少品牌、产品线、材料、颜色或内部SKU。")
                    sealed = int(raw.get("stock_spools") or 0)
                    opened = int(raw.get("opened_remaining_percent") or 0)
                    if sealed < 0 or not 0 <= opened <= 100:
                        raise InputError("库存导入行的未开封卷数或在用余量无效。")
                    sku = str(raw["sku"]).strip()
                    existing = connection.execute(
                        "SELECT * FROM filament_inventory_view WHERE owner_id=? AND lower(brand)=lower(?) AND sku=? AND region=?",
                        (owner, str(raw["brand"]).strip(), sku, str(raw.get("region") or "CN")),
                    ).fetchone()
                    now = _now()
                    color_family = str(raw.get("color_family") or _classify_color_family(raw.get("color")))
                    product_seed = {
                        "id": existing["id"] if existing else str(uuid4()),
                        "owner_id": owner,
                        "brand": str(raw["brand"]).strip(),
                        "manufacturer": raw.get("manufacturer"),
                        "seller": raw.get("seller"),
                        "product_line": str(raw["product_line"]).strip(),
                        "material_type": str(raw["material_type"]).strip(),
                        "variant": raw.get("variant"),
                        "diameter_mm": float(raw.get("diameter_mm") or 1.75),
                        "region": str(raw.get("region") or "CN"),
                        "status": "reviewed",
                        "created_at": now,
                        "updated_at": now,
                        "product_id": None,
                    }
                    product_id = self._ensure_product_for_filament(connection, product_seed)
                    if existing:
                        current = self._decode("filaments", existing)
                        changed = any(
                            (
                                key in {"stock_spools", "opened_remaining_percent"}
                                and int(current.get(key) or 0) != int(value)
                            )
                            or (
                                key not in {"stock_spools", "opened_remaining_percent"}
                                and str(current.get(key) or "") != str(value or "")
                            )
                            for key, value in {
                                "product_line": raw["product_line"],
                                "material_type": raw["material_type"],
                                "color": raw["color"],
                                "color_family": color_family,
                                "stock_spools": sealed,
                                "opened_remaining_percent": opened,
                            }.items()
                        )
                        if not changed:
                            unchanged += 1
                            continue
                        before_sealed = int(current.get("stock_spools") or 0)
                        connection.execute(
                            "UPDATE filaments SET product_id=?,color=?,color_family=?,stock_spools=?,opened_remaining_percent=?,updated_at=? WHERE id=?",
                            (product_id, raw["color"], color_family, sealed, opened, now, current["id"]),
                        )
                        delta = sealed - before_sealed
                        if delta:
                            connection.execute(
                                "INSERT INTO inventory_movements(id,owner_id,filament_id,movement_type,delta,before_spools,after_spools,note,reverses_movement_id,created_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
                                (str(uuid4()), owner, current["id"], "count", delta, before_sealed, sealed, "重新导入库存盘点表", None, now),
                            )
                        updated += 1
                        continue

                    filament_id = str(uuid4())
                    connection.execute(
                        "INSERT INTO filaments(id,owner_id,product_id,color,color_family,sku,stock_spools,opened_remaining_percent,spool_weight_g,low_stock_threshold,target_stock_spools,inventory_notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (filament_id, owner, product_id, str(raw["color"]).strip(), color_family, sku, 0, opened, int(raw.get("spool_weight_g") or 1000), 0, 0, "由库存盘点工作簿导入；小数部分已转换为一卷在用余量。", now, now),
                    )
                    if sealed:
                        self._apply_movement(
                            connection,
                            filament_id,
                            sealed,
                            "purchase",
                            "库存盘点工作簿初始导入",
                        )
                    inserted += 1
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        imported = inserted + updated + unchanged
        return {
            "rows": imported,
            "inserted": inserted,
            "updated": updated,
            "unchanged": unchanged,
            "stock_equivalent": round(
                sum(
                    int(row.get("stock_spools") or 0)
                    + int(row.get("opened_remaining_percent") or 0) / 100
                    for row in rows
                ),
                2,
            ),
        }

    def undo_inventory_movement(self, movement_id: str, approved: bool) -> dict[str, Any]:
        if not approved:
            raise InputError("撤销库存变动必须显式确认。")
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            target = connection.execute("SELECT * FROM inventory_movements WHERE id=?", (movement_id,)).fetchone()
            if not target or target["movement_type"] == "undo":
                raise InputError("没有找到可撤销的库存记录。")
            if connection.execute("SELECT 1 FROM inventory_movements WHERE reverses_movement_id=?", (movement_id,)).fetchone():
                raise InputError("该库存记录已经撤销。")
            latest = connection.execute("SELECT id FROM inventory_movements WHERE filament_id=? ORDER BY created_at DESC LIMIT 1", (target["filament_id"],)).fetchone()
            if not latest or latest["id"] != movement_id:
                raise InputError("只能撤销该耗材最近一次库存变动。")
            result = self._apply_movement(connection, target["filament_id"], -int(target["delta"]), "undo", "撤销库存变动", movement_id)
            connection.commit()
            result["reversed_movement_id"] = movement_id
            return result

    def health(self) -> dict[str, Any]:
        with self.connect() as connection:
            integrity = connection.execute("PRAGMA quick_check").fetchone()[0]
            counts = {table: int(connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0]) for table in TABLES}
        return {"integrity": integrity, "counts": counts, "database_path": str(self.config.database_path)}


_STORE_CACHE: dict[tuple[Path, Path, Path], LocalStore] = {}
_STORE_CACHE_LOCK = threading.Lock()


def store() -> LocalStore:
    config = LocalStoreConfig.from_environment()
    key = (config.database_path, config.files_root, config.migrations_root)
    with _STORE_CACHE_LOCK:
        current = _STORE_CACHE.get(key)
        if current is None:
            current = LocalStore(config)
            current.initialize()
            _STORE_CACHE[key] = current
    return current


def list_inventory() -> list[dict[str, Any]]: return store().list_inventory()
def list_dashboard_filaments() -> list[dict[str, Any]]: return store().list_dashboard_filaments()
def list_products() -> list[dict[str, Any]]: return store().list_products()
def get_product_detail(product_id: str) -> dict[str, Any]: return store().get_product_detail(product_id)
def get_filament_detail(filament_id: str) -> dict[str, Any]: return store().get_filament_detail(filament_id)
def create_filament_record(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().create_filament_record(*args, **kwargs)
def update_filament_record(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().update_filament_record(*args, **kwargs)
def adjust_inventory(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().adjust_inventory(*args, **kwargs)
def set_inventory_details(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().set_inventory_details(*args, **kwargs)
def list_inventory_movements(*args: Any, **kwargs: Any) -> list[dict[str, Any]]: return store().list_inventory_movements(*args, **kwargs)
def undo_inventory_movement(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().undo_inventory_movement(*args, **kwargs)
def import_inventory_rows(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().import_inventory_rows(*args, **kwargs)
def add_filament_evidence(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().add_evidence(*args, **kwargs)
def add_product_inbox_evidence(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().add_product_inbox_evidence(*args, **kwargs)
def process_product_inbox_evidence(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().process_product_inbox_evidence(*args, **kwargs)
def add_preset_evaluation(*args: Any, **kwargs: Any) -> dict[str, Any]: return store().add_preset_evaluation(*args, **kwargs)
def get_source_file(*args: Any, **kwargs: Any) -> tuple[Path, str | None, str]: return store().get_source_file(*args, **kwargs)


def set_inventory(filament_id: str, stock_spools: int, spool_weight_g: int | None, low_stock_threshold: int | None, approved: bool, opened_remaining_percent: int | None = None) -> dict[str, Any]:
    return set_inventory_details(
        filament_id,
        stock_spools,
        spool_weight_g,
        low_stock_threshold,
        None,
        None,
        None,
        "库存盘点",
        approved,
        opened_remaining_percent=opened_remaining_percent,
    )


def _copy_private_file(source: Path, destination: Path) -> str:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        shutil.copy2(source, destination)
    return destination.as_posix()


def commit_manifest(manifest_file: str | Path, approved: bool) -> dict[str, Any]:
    if not approved:
        raise InputError("commit必须显式传入--approved。")
    manifest_path, manifest = load_manifest(manifest_file)
    database = store()
    identity = manifest["filament"]
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        owner = database.owner_id(connection)
        if identity.get("barcode"):
            filament = connection.execute("SELECT * FROM filament_inventory_view WHERE barcode=?", (identity["barcode"],)).fetchone()
        else:
            filament = connection.execute("SELECT * FROM filament_inventory_view WHERE lower(brand)=lower(?) AND sku=? AND region=?", (identity["brand"], identity.get("sku"), identity["region"])).fetchone()
        if filament:
            filament_id = str(filament["id"])
        else:
            filament_id, timestamp = str(uuid4()), _now()
            product_seed = {
                "id": filament_id,
                "owner_id": owner,
                "brand": identity["brand"],
                "manufacturer": identity.get("manufacturer"),
                "seller": identity.get("seller"),
                "product_line": identity["product_line"],
                "material_type": identity["material_type"],
                "variant": identity.get("variant"),
                "diameter_mm": identity.get("diameter_mm", 1.75),
                "region": identity["region"],
                "status": "reviewed",
                "created_at": timestamp,
                "updated_at": timestamp,
                "product_id": None,
            }
            product_id = database._ensure_product_for_filament(connection, product_seed)
            connection.execute("INSERT INTO filaments(id,owner_id,product_id,color,color_family,sku,barcode,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?)", (filament_id, owner, product_id, identity.get("color"), _classify_color_family(identity.get("color")), identity.get("sku"), identity.get("barcode"), timestamp, timestamp))
            filament = connection.execute("SELECT * FROM filament_inventory_view WHERE id=?", (filament_id,)).fetchone()
        product_id = database._ensure_product_for_filament(connection, dict(filament))
        source_ids: dict[str, str] = {}
        added_sources = added_claims = 0
        for source in manifest["sources"]:
            found = connection.execute("SELECT id FROM sources WHERE product_id=? AND filament_id IS NULL AND sha256=?", (product_id, source["sha256"])).fetchone()
            if found:
                source_id = str(found["id"])
            else:
                source_id = str(uuid4())
                local = manifest_path.parent / source["staged_path"]
                relative = Path("evidence") / source["sha256"] / local.name
                _copy_private_file(local, database.config.files_root / relative)
                connection.execute("INSERT INTO sources(id,owner_id,product_id,filament_id,scope_level,kind,title,origin,source_organization,region,document_version,retrieved_at,media_type,sha256,storage_path,extracted_text_path,metadata,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (source_id, owner, product_id, None, "product", source["kind"], local.name, source["original"] if str(source["original"]).startswith(("http://","https://")) else Path(source["original"]).name, source.get("source_organization"), source.get("region"), source.get("document_version"), source.get("retrieved_at"), source.get("media_type"), source["sha256"], relative.as_posix(), source.get("extracted_text_path"), json.dumps({"size_bytes":source.get("size_bytes"),"authority":source.get("authority","unknown"),"notes":source.get("notes")}, ensure_ascii=False), _now()))
                added_sources += 1
            source_ids[source["source_ref"]] = source_id
        for claim in manifest["claims"]:
            if connection.execute("SELECT 1 FROM claims WHERE fingerprint=?", (claim["fingerprint"],)).fetchone(): continue
            timestamp = _now()
            connection.execute("INSERT INTO claims(id,owner_id,product_id,filament_id,source_id,scope_level,claim_key,value,unit,scope,source_location,authority,review_status,notes,fingerprint,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (str(uuid4()), owner, product_id, None, source_ids[claim["source_ref"]], "product", claim["key"], json.dumps(claim["value"],ensure_ascii=False), claim.get("unit"), json.dumps(claim.get("scope") or {},ensure_ascii=False), claim.get("location"), claim.get("authority","unknown"), claim.get("review_status","pending"), claim.get("notes"), claim["fingerprint"], timestamp, timestamp))
            added_claims += 1
        connection.commit()
    return {"filament_id":filament_id,"copied_sources":added_sources,"inserted_claims":added_claims,"conflicts":len(manifest.get("conflicts",[]))}


def commit_profile_report(report_file: str | Path, filament_id: str, approved: bool) -> dict[str, Any]:
    if not approved: raise InputError("预设建档必须显式传入--approved。")
    path = Path(report_file).expanduser().resolve()
    report = json.loads(path.read_text(encoding="utf-8"))
    database, timestamp = store(), _now()
    source_hash = str(report.get("source_snapshot_hash") or "official-profile")
    generator = str(report.get("generator_version") or "0.1.0")
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        database._one_filament(connection, filament_id)
        owner = database.owner_id(connection)
        existing = connection.execute("SELECT * FROM profile_builds WHERE filament_id=? AND target_printer=? AND nozzle_mm=? AND source_snapshot_hash=? AND generator_version=?", (filament_id,"Bambu Lab A1 0.4 nozzle",0.4,source_hash,generator)).fetchone()
        artifact_paths = json.loads(existing["artifact_paths"]) if existing else {}
        validation = report.get("validation") or {}
        for key,value in {"generated_json":report.get("generated_json"),"generated_bbsflmt":report.get("generated_bbsflmt"),"slice_output_3mf":validation.get("output_3mf"),"slice_result_json":validation.get("result_json")}.items():
            if value and key not in artifact_paths:
                local = Path(value).expanduser().resolve()
                if not local.is_file(): raise InputError(f"预设产物不存在：{local}")
                relative = Path("artifacts") / filament_id / source_hash / local.name
                _copy_private_file(local, database.config.files_root / relative)
                artifact_paths[key] = relative.as_posix()
        if existing:
            connection.execute("UPDATE profile_builds SET status=?,validation=?,diff=?,artifact_paths=?,updated_at=? WHERE id=?", (report.get("status"),json.dumps(validation,ensure_ascii=False),json.dumps(report.get("changes") or [],ensure_ascii=False),json.dumps(artifact_paths,ensure_ascii=False),timestamp,existing["id"]))
            profile_id, created = str(existing["id"]), False
        else:
            profile_id, created = str(uuid4()), True
            connection.execute("INSERT INTO profile_builds(id,owner_id,filament_id,target_printer,nozzle_mm,baseline_name,baseline_sha256,generator_version,source_snapshot_hash,settings,diff,status,validation,artifact_paths,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (profile_id,owner,filament_id,"Bambu Lab A1 0.4 nozzle",0.4,report.get("baseline_name") or "unknown",report.get("baseline_sha256"),generator,source_hash,json.dumps(report.get("settings"),ensure_ascii=False) if report.get("settings") is not None else None,json.dumps(report.get("changes") or [],ensure_ascii=False),report.get("status"),json.dumps(validation,ensure_ascii=False),json.dumps(artifact_paths,ensure_ascii=False),timestamp,timestamp))
        connection.commit()
    return {"profile_build_id":profile_id,"created":created,"updated":not created}


def commit_calibration_record(record_file: str | Path, filament_id: str, profile_build_id: str | None, approved: bool) -> dict[str, Any]:
    if not approved: raise InputError("校准建档必须显式传入--approved。")
    record = json.loads(Path(record_file).expanduser().resolve().read_text(encoding="utf-8"))
    database = store()
    with database.connect() as connection:
        connection.execute("BEGIN IMMEDIATE")
        database._one_filament(connection, filament_id)
        existing = connection.execute("SELECT id FROM calibration_runs WHERE fingerprint=?", (record["fingerprint"],)).fetchone()
        if existing:
            connection.rollback(); return {"calibration_run_id":existing["id"],"created":False}
        artifact_path = None
        if record.get("artifact_path"):
            local = Path(record["artifact_path"]).expanduser().resolve()
            relative = Path("artifacts") / filament_id / "calibrations" / record["fingerprint"] / local.name
            _copy_private_file(local, database.config.files_root / relative); artifact_path = relative.as_posix()
        row_id = str(uuid4())
        connection.execute("INSERT INTO calibration_runs(id,owner_id,filament_id,profile_build_id,machine,nozzle_mm,hotend,plate,lot,drying,environment,test_type,result,artifact_path,fingerprint,status,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (row_id,database.owner_id(connection),filament_id,profile_build_id,record["machine"],record["nozzle_mm"],record.get("hotend"),record.get("plate"),record.get("lot"),json.dumps(record.get("drying") or {},ensure_ascii=False),json.dumps(record.get("environment") or {},ensure_ascii=False),record["test_type"],json.dumps(record["result"],ensure_ascii=False),artifact_path,record["fingerprint"],record.get("status","recorded"),_now()))
        connection.commit()
    return {"calibration_run_id":row_id,"created":True}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def backup_local_data(
    output_dir: str | Path = "backups", keep: int | None = None
) -> dict[str, Any]:
    """Create a consistent, self-verifying archive without stopping the service."""
    database = store()
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"printpilot-material-lab-{timestamp}.tar.gz"

    with tempfile.TemporaryDirectory(prefix="printpilot-backup-") as temporary:
        root = Path(temporary) / "printpilot-material-lab"
        root.mkdir()
        snapshot = root / "material-lab.sqlite3"
        with database.connect() as source, closing(sqlite3.connect(snapshot)) as target:
            source.backup(target)
        files_target = root / "files"
        if database.config.files_root.is_dir():
            shutil.copytree(database.config.files_root, files_target)
        else:
            files_target.mkdir()

        hashes: dict[str, str] = {}
        for item in sorted(path for path in root.rglob("*") if path.is_file()):
            relative = item.relative_to(root).as_posix()
            hashes[relative] = _sha256_file(item)
        manifest = {
            "format": "printpilot-material-lab-backup-v1",
            "created_at": _now(),
            "owner_id": database.owner_id(),
            "files": hashes,
            "health": database.health(),
        }
        (root / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with tarfile.open(archive, "w:gz") as bundle:
            bundle.add(root, arcname="printpilot-material-lab")

    removed: list[str] = []
    if keep is not None:
        if keep < 1 or keep > 3650:
            raise InputError("备份保留数量必须在1到3650之间。")
        archives = sorted(
            destination.glob("printpilot-material-lab-*.tar.gz"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        for expired in archives[keep:]:
            expired.unlink()
            removed.append(expired.name)
    return {
        "archive": str(archive),
        "sha256": _sha256_file(archive),
        "size_bytes": archive.stat().st_size,
        "health": database.health(),
        "removed_old_backups": removed,
    }


def _safe_extract(bundle: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    members = bundle.getmembers()
    for member in members:
        target = (destination / member.name).resolve()
        if root not in target.parents and target != root:
            raise InputError("备份包包含不安全路径，已拒绝恢复。")
        if not (member.isfile() or member.isdir()):
            raise InputError("备份包包含链接或特殊文件，已拒绝恢复。")
    options: dict[str, Any] = {}
    if "filter" in inspect.signature(bundle.extractall).parameters:
        options["filter"] = "fully_trusted"
    bundle.extractall(destination, members=members, **options)


def restore_local_data(archive_file: str | Path, approved: bool) -> dict[str, Any]:
    """Validate completely, then atomically replace the database and file tree."""
    if not approved:
        raise InputError("恢复会覆盖当前数据，必须显式传入--approved。")
    archive = Path(archive_file).expanduser().resolve()
    if not archive.is_file():
        raise InputError(f"备份文件不存在：{archive}")
    database = LocalStore()

    with tempfile.TemporaryDirectory(prefix="printpilot-restore-") as temporary:
        temporary_root = Path(temporary)
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                _safe_extract(bundle, temporary_root)
        except (tarfile.TarError, OSError) as exc:
            raise InputError("备份包无法读取或格式不正确。") from exc
        root = temporary_root / "printpilot-material-lab"
        manifest_path = root / "manifest.json"
        snapshot = root / "material-lab.sqlite3"
        restored_files = root / "files"
        if not manifest_path.is_file() or not snapshot.is_file() or not restored_files.is_dir():
            raise InputError("备份包缺少数据库、私有文件或清单。")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != "printpilot-material-lab-backup-v1":
            raise InputError("不支持的备份格式。")
        expected = manifest.get("files")
        if not isinstance(expected, dict):
            raise InputError("备份校验清单无效。")
        actual = {
            path.relative_to(root).as_posix(): _sha256_file(path)
            for path in sorted(root.rglob("*"))
            if path.is_file() and path != manifest_path
        }
        if actual != expected:
            raise InputError("备份内容校验失败，已拒绝恢复。")
        with closing(sqlite3.connect(snapshot)) as connection:
            if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                raise InputError("备份中的SQLite数据库完整性检查失败。")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if not set(TABLES).issubset(tables) or "app_metadata" not in tables:
                raise InputError("备份数据库结构不完整。")

        database.config.database_path.parent.mkdir(parents=True, exist_ok=True)
        database.config.files_root.parent.mkdir(parents=True, exist_ok=True)
        rollback_root = Path(temporary) / "rollback"
        rollback_root.mkdir()
        old_database = rollback_root / "material-lab.sqlite3"
        old_files = rollback_root / "files"
        if database.config.database_path.exists():
            shutil.copy2(database.config.database_path, old_database)
        if database.config.files_root.exists():
            shutil.copytree(database.config.files_root, old_files)
        try:
            shutil.copy2(snapshot, database.config.database_path)
            staging_files = database.config.files_root.with_name(
                f"{database.config.files_root.name}.restore-{uuid4().hex}"
            )
            shutil.copytree(restored_files, staging_files)
            if database.config.files_root.exists():
                shutil.rmtree(database.config.files_root)
            staging_files.replace(database.config.files_root)
            for suffix in ("-wal", "-shm"):
                database.config.database_path.with_name(
                    database.config.database_path.name + suffix
                ).unlink(missing_ok=True)
            health = database.health()
            if health["integrity"] != "ok":
                raise DatabaseError("恢复后的数据库完整性检查失败。")
        except Exception:
            if old_database.exists():
                shutil.copy2(old_database, database.config.database_path)
            if database.config.files_root.exists():
                shutil.rmtree(database.config.files_root)
            if old_files.exists():
                shutil.copytree(old_files, database.config.files_root)
            raise
    return {"restored_from": str(archive), "health": health}


def local_health() -> dict[str, Any]:
    return store().health()
