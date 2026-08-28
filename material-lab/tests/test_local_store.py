from __future__ import annotations

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from printpilot_material_lab.errors import InputError
from printpilot_material_lab.local_store import (
    LocalStore,
    LocalStoreConfig,
    backup_local_data,
    restore_local_data,
)
from printpilot_material_lab.preset_evaluation import evaluate_preset_bytes, evaluate_preset_file


OWNER_ID = "00000000-0000-4000-8000-000000000001"


@pytest.fixture
def database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LocalStore:
    monkeypatch.setenv("PRINTPILOT_DATA_DIR", str(tmp_path / "data"))
    store = LocalStore(LocalStoreConfig.from_environment())
    assert store.initialize(OWNER_ID) == OWNER_ID
    return store


def _create(database: LocalStore, *, sku: str = "R3D-CLEAR-CN") -> dict[str, object]:
    return database.create_filament_record(
        {
            "brand": "R3D",
            "manufacturer": "R3D",
            "seller": "国内官方渠道",
            "product_line": "PETG透明系列",
            "material_type": "PETG",
            "variant": "Transparent",
            "color": "透明",
            "diameter_mm": 1.75,
            "sku": sku,
            "barcode": None,
            "region": "CN",
            "status": "reviewed",
        },
        stock_spools=6,
        spool_weight_g=1000,
        low_stock_threshold=1,
        target_stock_spools=8,
        storage_location="耗材架A1",
        inventory_notes="首批六卷",
        approved=True,
    )


def test_product_facts_are_shared_while_color_records_stay_separate(
    database: LocalStore,
) -> None:
    clear = _create(database)
    black = database.create_filament_record(
        {
            "brand": "R3D",
            "manufacturer": "R3D",
            "seller": "国内官方渠道",
            "product_line": "PETG透明系列",
            "material_type": "PETG",
            "variant": "Transparent",
            "color": "黑色",
            "diameter_mm": 1.75,
            "sku": "R3D-BLACK-CN",
            "barcode": None,
            "region": "CN",
            "status": "reviewed",
        },
        stock_spools=1,
        opened_remaining_percent=0,
        spool_weight_g=1000,
        low_stock_threshold=0,
        target_stock_spools=1,
        storage_location=None,
        inventory_notes=None,
        approved=True,
    )
    products = database.list_products()
    assert len(products) == 1
    assert products[0]["color_count"] == 2
    assert clear["product_id"] == black["product_id"] == products[0]["product_id"]

    database.add_evidence(
        str(clear["filament_id"]),
        {"kind": "manufacturer", "title": "R3D TDS"},
        [{"key": "nozzle_temperature", "value": "230-260", "unit": "°C"}],
        None,
        None,
        None,
        True,
    )
    black_detail = database.get_filament_detail(str(black["filament_id"]))
    assert [claim["claim_key"] for claim in black_detail["claims"]] == [
        "nozzle_temperature"
    ]
    product_detail = database.get_product_detail(str(products[0]["product_id"]))
    assert product_detail["summary"]["product_claim_count"] == 1
    assert len(product_detail["sources"]) == 1


def test_color_evidence_does_not_leak_to_other_colors(database: LocalStore) -> None:
    clear = _create(database)
    black = database.create_filament_record(
        {
            "brand": "R3D",
            "manufacturer": "R3D",
            "seller": "国内官方渠道",
            "product_line": "PETG透明系列",
            "material_type": "PETG",
            "variant": "Transparent",
            "color": "黑色",
            "diameter_mm": 1.75,
            "sku": "R3D-BLACK-COLOR-SCOPE",
            "barcode": None,
            "region": "CN",
            "status": "reviewed",
        },
        stock_spools=1,
        spool_weight_g=1000,
        low_stock_threshold=0,
        target_stock_spools=1,
        storage_location=None,
        inventory_notes=None,
        approved=True,
    )
    database.add_evidence(
        str(clear["filament_id"]),
        {
            "kind": "user_note",
            "scope_level": "color_variant",
            "title": "透明色温度塔",
        },
        [{"key": "temperature_tower_best", "value": 245, "unit": "°C"}],
        None,
        None,
        None,
        True,
    )
    clear_detail = database.get_filament_detail(str(clear["filament_id"]))
    black_detail = database.get_filament_detail(str(black["filament_id"]))
    assert [item["claim_key"] for item in clear_detail["claims"]] == [
        "temperature_tower_best"
    ]
    assert black_detail["claims"] == []
    product_detail = database.get_product_detail(str(clear["product_id"]))
    assert product_detail["summary"]["product_claim_count"] == 0
    assert product_detail["summary"]["color_claim_count"] == 1
    assert product_detail["sources"][0]["scope_level"] == "color_variant"


def test_manufacturer_preset_can_be_product_or_color_scoped(
    database: LocalStore,
) -> None:
    clear = _create(database)
    product_id = str(clear["product_id"])
    product_bytes = json.dumps(
        {
            "name": "Polymaker PETG @Bambu Lab A1 0.4 nozzle",
            "from": "User",
            "filament_vendor": ["Polymaker"],
            "filament_type": ["PETG"],
            "filament_flow_ratio": ["0.95"],
            "filament_max_volumetric_speed": ["11"],
            "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
        }
    ).encode()
    product_profile = evaluate_preset_bytes(
        "Polymaker PETG.json",
        product_bytes,
        authority="manufacturer_profile",
        provenance="厂家提供，用户转存",
    )["profiles"][0]
    result = database.add_preset_evaluation(
        product_id,
        None,
        product_profile,
        product_bytes,
        "Polymaker PETG.json",
        True,
    )
    assert result["created"] is True

    color_bytes = json.dumps(
        {
            "name": "PETG HF Clear @Bambu Lab A1 0.4 nozzle",
            "from": "User",
            "filament_vendor": ["NextShapes"],
            "filament_type": ["PETG"],
            "filament_flow_ratio": ["1"],
            "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
        }
    ).encode()
    color_profile = evaluate_preset_bytes(
        "PETG HF Clear.json",
        color_bytes,
        authority="manufacturer_profile",
        provenance="厂家提供，用户转存",
    )["profiles"][0]
    database.add_preset_evaluation(
        product_id,
        str(clear["filament_id"]),
        color_profile,
        color_bytes,
        "PETG HF Clear.json",
        True,
    )
    detail = database.get_product_detail(product_id)
    assert {item["scope_level"] for item in detail["presets"]} == {
        "product",
        "color_variant",
    }
    assert detail["summary"]["preset_count"] == 2
    assert database.list_products()[0]["source_count"] == 2


def test_sqlite_inventory_transactions_and_undo(database: LocalStore) -> None:
    filament_id = str(_create(database)["filament_id"])
    assert database.health()["integrity"] == "ok"
    assert database.list_inventory()[0]["stock_spools"] == 6

    purchase = database.adjust_inventory(
        filament_id, 2, True, movement_type="purchase", note="补货"
    )
    movement_id = purchase["movement"]["movement_id"]
    assert purchase["after"]["stock_spools"] == 8
    assert database.undo_inventory_movement(movement_id, True)["after_spools"] == 6
    assert database.list_inventory_movements(filament_id, 10)[0]["movement_type"] == "undo"

    with pytest.raises(InputError, match="已经撤销"):
        database.undo_inventory_movement(movement_id, True)
    with pytest.raises(InputError, match="库存不足"):
        database.adjust_inventory(filament_id, -7, True, movement_type="usage")


def test_sqlite_duplicate_identity_is_rejected(database: LocalStore) -> None:
    _create(database)
    with pytest.raises(InputError, match="已经存在"):
        _create(database)
    assert database.health()["counts"]["filaments"] == 1


def test_smart_import_can_create_record_without_supplier_identity(database: LocalStore) -> None:
    created = database.create_filament_record(
        {
            "brand": "待识别品牌",
            "manufacturer": None,
            "seller": "遇果",
            "product_line": "PETG 黑色参数资料",
            "material_type": "PETG",
            "variant": None,
            "color": "黑色",
            "diameter_mm": 1.75,
            "sku": None,
            "barcode": None,
            "region": "CN",
            "status": "staged",
        },
        stock_spools=0,
        spool_weight_g=1000,
        low_stock_threshold=1,
        target_stock_spools=1,
        storage_location=None,
        inventory_notes=None,
        approved=True,
    )
    assert str(created["sku"]).startswith("PP-AUTO-")
    assert "系统自动生成内部标识" in str(created["inventory_notes"])


def test_inventory_tracks_sealed_and_one_opened_spool(database: LocalStore) -> None:
    filament_id = str(_create(database, sku="OPENED-PETG")['filament_id'])
    result = database.set_inventory_details(
        filament_id,
        5,
        1000,
        1,
        8,
        "耗材架A1",
        None,
        "开封一卷",
        True,
        opened_remaining_percent=65,
    )
    assert result["after"]["stock_spools"] == 5
    assert result["after"]["opened_remaining_percent"] == 65
    assert result["after"]["stock_equivalent"] == 5.65
    assert result["after"]["stock_total_kg"] == 5.65


def test_evidence_upload_preserves_customer_quote_claims_and_deduplicates(
    database: LocalStore,
) -> None:
    filament_id = str(_create(database, sku="YU-GPETG-BLACK")['filament_id'])
    source = {
        "kind": "customer_service",
        "title": "遇果常规PETG黑色客服回复",
        "source_organization": "遇果",
        "origin": "订单客服",
        "user_decision": "use_default_profile",
        "quote": "按照默认参数打就行",
        "notes": "先按拓竹默认PETG预设打印。",
    }
    claims = [{"key": "nozzle_temperature", "value": "230-260", "unit": "°C"}]
    first = database.add_evidence(
        filament_id,
        source,
        claims,
        b"fake screenshot bytes",
        "customer-service.png",
        "image/png",
        True,
    )
    assert first["inserted_claims"] == 2
    detail = database.get_filament_detail(filament_id)
    assert len(detail["sources"]) == 1
    assert "storage_path" not in detail["sources"][0]
    assert detail["sources"][0]["metadata"]["user_decision"] == "use_default_profile"
    assert {claim["claim_key"] for claim in detail["claims"]} == {
        "customer_quote",
        "nozzle_temperature",
    }
    quote = next(claim for claim in detail["claims"] if claim["claim_key"] == "customer_quote")
    assert quote["value"] == "按照默认参数打就行"
    assert "storage_path" not in (quote["source"] or {})
    source_path, media_type, _ = database.get_source_file(str(first["source_id"]))
    assert source_path.read_bytes() == b"fake screenshot bytes"
    assert media_type == "image/png"

    second = database.add_evidence(
        filament_id,
        source,
        claims,
        b"fake screenshot bytes",
        "customer-service.png",
        "image/png",
        True,
    )
    assert second["deduplicated_source"] is True
    assert second["inserted_claims"] == 0
    assert database.health()["counts"]["sources"] == 1
    assert database.health()["counts"]["claims"] == 2


def test_product_inbox_archives_raw_image_without_creating_claims(
    database: LocalStore,
) -> None:
    created = _create(database, sku="R3D-INBOX")
    product_id = str(created["product_id"])
    image = b"\x89PNG\r\n\x1a\nraw screenshot"
    first = database.add_product_inbox_evidence(
        product_id,
        {
            "kind": "seller",
            "title": "国内商品页参数图",
            "source_organization": "R3D官方店",
            "region": "CN",
            "notes": "等待人工整理",
        },
        image,
        "product-page.png",
        "image/png",
        True,
    )
    detail = database.get_product_detail(product_id)
    assert first["processing_status"] == "pending_manual_review"
    assert first["inserted_claims"] == 0
    assert detail["product_claims"] == []
    assert len(detail["sources"]) == 1
    assert detail["sources"][0]["metadata"] == {
        "processing_status": "pending_manual_review",
        "uploaded_from": "product_inbox",
        "filename": "product-page.png",
        "notes": "等待人工整理",
    }
    source_path, media_type, _ = database.get_source_file(str(first["source_id"]))
    assert source_path.read_bytes() == image
    assert media_type == "image/png"

    second = database.add_product_inbox_evidence(
        product_id,
        {"kind": "seller", "title": "重复上传"},
        image,
        "duplicate.png",
        "image/png",
        True,
    )
    assert second["deduplicated_source"] is True
    assert database.health()["counts"]["sources"] == 1
    assert database.health()["counts"]["claims"] == 0


def test_product_inbox_can_be_processed_without_reuploading_source(
    database: LocalStore,
) -> None:
    created = _create(database, sku="R3D-PROCESSED")
    product_id = str(created["product_id"])
    archived = database.add_product_inbox_evidence(
        product_id,
        {"kind": "seller", "title": "颜色目录", "source_organization": "R3D"},
        b"\x89PNG\r\n\x1a\ncolor catalog",
        "colors.png",
        "image/png",
        True,
    )
    claims = [
        {"key": "available_colors", "value": ["透明", "黑色", "白色"]},
        {"key": "tensile_strength", "value": {"value": 41, "tolerance": 2}, "unit": "MPa"},
    ]
    first = database.process_product_inbox_evidence(
        str(archived["source_id"]), claims, "系列颜色：透明、黑色、白色", True
    )
    second = database.process_product_inbox_evidence(
        str(archived["source_id"]), claims, "系列颜色：透明、黑色、白色", True
    )
    detail = database.get_product_detail(product_id)
    assert first["inserted_claims"] == 2
    assert second["inserted_claims"] == 0
    assert len(detail["sources"]) == 1
    assert detail["sources"][0]["metadata"]["processing_status"] == "processed"
    assert {claim["claim_key"] for claim in detail["product_claims"]} == {
        "available_colors",
        "tensile_strength",
    }
    extracted = database.config.files_root / str(first["extracted_text_path"])
    assert extracted.read_text(encoding="utf-8") == "系列颜色：透明、黑色、白色"


def test_preset_evaluation_expands_local_bambu_inheritance(tmp_path: Path) -> None:
    root = tmp_path / "filament"
    vendor = root / "SUNLU"
    vendor.mkdir(parents=True)
    (root / "fdm_filament_pla.json").write_text(
        json.dumps({"name": "fdm_filament_pla", "nozzle_temperature": ["220"]}),
        encoding="utf-8",
    )
    (vendor / "SUNLU PLA+ 2.0 @base.json").write_text(
        json.dumps({
            "name": "SUNLU PLA+ 2.0 @base",
            "inherits": "fdm_filament_pla",
            "filament_vendor": ["SUNLU"],
            "filament_density": ["1.21"],
            "filament_max_volumetric_speed": ["22"],
            "temperature_vitrification": ["54"],
        }),
        encoding="utf-8",
    )
    child = vendor / "SUNLU PLA+ 2.0 @BBL A1.json"
    child.write_text(
        json.dumps({
            "name": "SUNLU PLA+ 2.0 @BBL A1",
            "inherits": "SUNLU PLA+ 2.0 @base",
            "from": "system",
            "fan_min_speed": ["60"],
            "fan_max_speed": ["80"],
            "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
        }),
        encoding="utf-8",
    )
    profile = evaluate_preset_file(
        child, authority="bambu_system", provenance="Bambu Studio内置"
    )["profiles"][0]
    assert profile["settings"]["nozzle_temperature"] == "220"
    assert profile["settings"]["filament_density"] == "1.21"
    assert profile["settings"]["temperature_vitrification"] == "54"
    assert profile["settings"]["fan_min_speed"] == "60"
    assert "fdm_filament_pla" in profile["warnings"][-1]


def test_concurrent_inventory_updates_do_not_lose_movements(database: LocalStore) -> None:
    filament_id = str(_create(database)["filament_id"])
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _: database.adjust_inventory(
                    filament_id, 1, True, movement_type="purchase"
                ),
                range(24),
            )
        )
    assert len(results) == 24
    assert database.list_inventory()[0]["stock_spools"] == 30
    assert len(database.list_inventory_movements(filament_id, 50)) == 25


def test_backup_is_verified_and_restore_rolls_back_data(
    database: LocalStore, tmp_path: Path
) -> None:
    filament_id = str(_create(database)["filament_id"])
    private_file = database.config.files_root / "evidence" / "sample.pdf"
    private_file.parent.mkdir(parents=True)
    private_file.write_bytes(b"private evidence")

    archive = Path(backup_local_data(tmp_path / "backups")["archive"])
    database.adjust_inventory(filament_id, -2, True, movement_type="usage")
    private_file.write_bytes(b"changed")

    restored = restore_local_data(archive, approved=True)
    assert restored["health"]["integrity"] == "ok"
    assert database.list_inventory()[0]["stock_spools"] == 6
    assert private_file.read_bytes() == b"private evidence"


def test_restore_rejects_tampered_archive(database: LocalStore, tmp_path: Path) -> None:
    _create(database)
    archive = Path(backup_local_data(tmp_path / "backups")["archive"])
    payload = bytearray(archive.read_bytes())
    payload[len(payload) // 2] ^= 0xFF
    archive.write_bytes(payload)
    with pytest.raises(InputError, match="无法读取|校验失败"):
        restore_local_data(archive, approved=True)
