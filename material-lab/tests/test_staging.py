from __future__ import annotations

import json
from pathlib import Path

import pytest

from printpilot_material_lab.errors import InputError
from printpilot_material_lab.staging import detect_conflicts, stage_material


def _write_json(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    return path


def test_stage_deduplicates_files_and_preserves_conflicts(tmp_path: Path) -> None:
    identity = _write_json(
        tmp_path / "identity.json",
        {
            "brand": "R3D",
            "product_line": "PETG Transparent",
            "material_type": "PETG",
            "sku": "R3D-CLEAR",
            "region": "global",
        },
    )
    source = _write_json(tmp_path / "source.json", {"temperature": [230, 260]})
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(source.read_bytes())
    claims = _write_json(
        tmp_path / "claims.json",
        [
            {
                "key": "minimum_nozzle_mm",
                "value": 0.2,
                "unit": "mm",
                "source": "source.json",
                "scope": {"region": "global"},
            },
            {
                "key": "minimum_nozzle_mm",
                "value": 0.3,
                "unit": "mm",
                "source": "source.json",
                "scope": {"region": "CN"},
            },
        ],
    )

    manifest_path = stage_material(
        identity, [str(source), str(duplicate)], claims, tmp_path / "staging"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert len(manifest["sources"]) == 1
    assert [item["key"] for item in manifest["conflicts"]] == ["minimum_nozzle_mm"]
    assert (manifest_path.parent / "review.md").is_file()


def test_stage_rejects_unknown_claim_source(tmp_path: Path) -> None:
    identity = _write_json(
        tmp_path / "identity.json",
        {
            "brand": "Vendor",
            "product_line": "PLA",
            "material_type": "PLA",
            "sku": "PLA-1",
            "region": "CN",
        },
    )
    source = _write_json(tmp_path / "source.json", {})
    claims = _write_json(
        tmp_path / "claims.json",
        [{"key": "density_g_cm3", "value": 1.2, "source": "missing.pdf"}],
    )
    with pytest.raises(InputError, match="未知来源"):
        stage_material(identity, [str(source)], claims, tmp_path / "staging")


def test_claim_can_reference_a_deduplicated_source_alias(tmp_path: Path) -> None:
    identity = _write_json(
        tmp_path / "identity.json",
        {
            "brand": "Vendor",
            "product_line": "PETG",
            "material_type": "PETG",
            "sku": "PETG-1",
            "region": "CN",
        },
    )
    source = _write_json(tmp_path / "source.json", {"density": 1.27})
    duplicate = tmp_path / "duplicate.json"
    duplicate.write_bytes(source.read_bytes())
    claims = _write_json(
        tmp_path / "claims.json",
        [{"key": "density_g_cm3", "value": 1.27, "source": "duplicate.json"}],
    )

    manifest_path = stage_material(
        identity, [str(source), str(duplicate)], claims, tmp_path / "staging"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert len(manifest["sources"]) == 1
    assert manifest["claims"][0]["source_ref"] == "source-01"


def test_detect_conflicts_ignores_rejected_values() -> None:
    claims = [
        {"key": "density_g_cm3", "value": 1.27, "unit": "g/cm3", "source_ref": "a"},
        {
            "key": "density_g_cm3",
            "value": 1.25,
            "unit": "g/cm3",
            "source_ref": "b",
            "review_status": "rejected",
        },
    ]
    assert detect_conflicts(claims) == []


def test_stage_preserves_source_identity_metadata(tmp_path: Path) -> None:
    identity = _write_json(
        tmp_path / "identity.json",
        {
            "brand": "Vendor",
            "product_line": "PETG",
            "material_type": "PETG",
            "region": "CN",
        },
    )
    source = _write_json(tmp_path / "profile.json", {"name": "Vendor PETG"})
    metadata = _write_json(
        tmp_path / "source-metadata.json",
        {
            "profile.json": {
                "authority": "manufacturer_profile",
                "source_organization": "Vendor",
                "document_version": "1.0",
            }
        },
    )
    manifest_path = stage_material(
        identity,
        [str(source)],
        None,
        tmp_path / "staging",
        source_metadata_file=metadata,
    )
    staged = json.loads(manifest_path.read_text(encoding="utf-8"))["sources"][0]
    assert staged["authority"] == "manufacturer_profile"
    assert staged["source_organization"] == "Vendor"
