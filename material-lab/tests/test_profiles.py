from __future__ import annotations

import json
import zipfile
from pathlib import Path

import pytest

from printpilot_material_lab.errors import ProfileBuildError
from printpilot_material_lab.profiles import build_profile
from printpilot_material_lab.util import fingerprint


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


def _bambu_home(
    tmp_path: Path, include_sunlu: bool = False, include_polylite: bool = False
) -> Path:
    home = tmp_path / "Bambu Studio"
    (home / "bambu-studio.exe").parent.mkdir(parents=True)
    (home / "bambu-studio.exe").write_bytes(b"")
    root = home / "resources" / "profiles" / "BBL" / "filament"
    base = {
        "type": "filament",
        "name": "fdm_filament_pet",
        "from": "system",
        "filament_type": ["PETG"],
        "filament_vendor": ["Generic"],
        "filament_flow_ratio": ["0.95"],
        "filament_max_volumetric_speed": ["6"],
        "nozzle_temperature": ["245"],
        "nozzle_temperature_range_low": ["230"],
        "nozzle_temperature_range_high": ["270"],
        "fan_min_speed": ["10"],
        "fan_max_speed": ["30"],
    }
    _write(root / "fdm_filament_pet.json", base)
    _write(
        root / "Bambu PETG Translucent @base.json",
        {
            "name": "Bambu PETG Translucent @base",
            "inherits": "fdm_filament_pet",
            "filament_vendor": ["Bambu Lab"],
            "filament_density": ["1.25"],
        },
    )
    _write(
        root / "Bambu PETG Translucent @BBL A1.json",
        {
            "name": "Bambu PETG Translucent @BBL A1",
            "inherits": "Bambu PETG Translucent @base",
            "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
        },
    )
    _write(
        root / "Generic PETG @BBL A1.json",
        {
            "name": "Generic PETG @BBL A1",
            "inherits": "fdm_filament_pet",
            "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
        },
    )
    if include_sunlu:
        _write(
            root / "SUNLU" / "SUNLU PETG @base.json",
            {
                "name": "SUNLU PETG @base",
                "inherits": "fdm_filament_pet",
                "filament_vendor": ["SUNLU"],
            },
        )
        _write(
            root / "SUNLU" / "SUNLU PETG @BBL A1.json",
            {
                "name": "SUNLU PETG @BBL A1",
                "inherits": "SUNLU PETG @base",
                "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
            },
        )
    if include_polylite:
        _write(
            root / "Polymaker" / "PolyLite PETG @BBL A1.json",
            {
                "name": "PolyLite PETG @BBL A1",
                "inherits": "fdm_filament_pet",
                "filament_vendor": ["Polymaker"],
                "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
            },
        )
    return home


def _manifest(path: Path, brand: str = "R3D") -> Path:
    data = {
        "schema_version": 1,
        "manifest_fingerprint": fingerprint({"brand": brand}),
        "filament": {
            "brand": brand,
            "manufacturer": brand,
            "product_line": "PETG" if brand == "SUNLU" else "PETG Transparent",
            "material_type": "PETG",
            "variant": "Transparent" if brand == "R3D" else None,
            "color": "Clear" if brand == "R3D" else None,
            "sku": f"{brand}-1",
            "barcode": None,
            "diameter_mm": 1.75,
            "region": "global",
        },
        "claims": [
            {
                "key": "density_g_cm3",
                "value": 1.27,
                "unit": "g/cm3",
                "source_ref": "pdf",
                "authority": "manufacturer_tds",
                "review_status": "approved",
            },
            {
                "key": "fan_speed_range_percent",
                "value": [10, 40],
                "unit": "%",
                "source_ref": "pdf",
                "authority": "manufacturer_tds",
                "review_status": "approved",
            },
            {
                "key": "max_print_speed_mm_s",
                "value": 300,
                "unit": "mm/s",
                "source_ref": "pdf",
                "authority": "manufacturer_tds",
                "review_status": "approved",
            },
        ],
        "conflicts": [],
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_r3d_build_uses_translucent_baseline_without_inventing_mvs(tmp_path: Path) -> None:
    report_path = build_profile(
        _manifest(tmp_path / "manifest.json"),
        tmp_path / "out",
        bambu_home=_bambu_home(tmp_path),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["baseline_name"] == "Bambu PETG Translucent @BBL A1"
    assert report["settings"]["filament_max_volumetric_speed"] == ["6"]
    assert report["settings"]["filament_density"] == ["1.27"]
    assert report["settings"]["fan_max_speed"] == ["30"]
    assert report["settings"]["cool_plate_temp"] == ["65"]
    assert report["settings"]["cool_plate_temp_initial_layer"] == ["65"]
    assert report["plate_policy"]["range_c"] == [60, 75]
    assert report["verified_claims"][0]["result"] == "baseline_within_range"
    assert any(item["key"] == "max_print_speed_mm_s" for item in report["ignored_claims"])
    assert Path(report["generated_json"]).is_file()
    bundle = Path(report["generated_bbsflmt"])
    with zipfile.ZipFile(bundle) as archive:
        assert "bundle_structure.json" in archive.namelist()


def test_exact_bambu_vendor_profile_is_reused(tmp_path: Path) -> None:
    report_path = build_profile(
        _manifest(tmp_path / "manifest.json", brand="SUNLU"),
        tmp_path / "out",
        bambu_home=_bambu_home(tmp_path, include_sunlu=True),
        plate_policy="baseline",
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["status"] == "official_profile_available"
    assert report["official_match"]["name"] == "SUNLU PETG @BBL A1"
    assert "generated_json" not in report


def test_glacier_policy_derives_from_exact_official_profile(tmp_path: Path) -> None:
    report_path = build_profile(
        _manifest(tmp_path / "manifest.json", brand="SUNLU"),
        tmp_path / "out",
        bambu_home=_bambu_home(tmp_path, include_sunlu=True),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["official_match"]["used_as_baseline"] is True
    assert report["settings"]["cool_plate_temp"] == ["65"]
    assert Path(report["generated_json"]).is_file()


def test_manufacturer_target_profile_precedes_generic_baseline(tmp_path: Path) -> None:
    evidence = tmp_path / "evidence" / "vendor-profile.json"
    manufacturer_profile = {
        "type": "filament",
        "name": "Vendor PETG @Bambu Lab A1 0.4 nozzle",
        "filament_type": ["PETG"],
        "filament_vendor": ["Vendor"],
        "filament_flow_ratio": ["0.97"],
        "filament_max_volumetric_speed": ["12"],
        "nozzle_temperature": ["250"],
        "compatible_printers": ["Bambu Lab A1 0.4 nozzle"],
    }
    _write(evidence, manufacturer_profile)
    manifest = {
        "schema_version": 1,
        "manifest_fingerprint": fingerprint({"brand": "Vendor"}),
        "filament": {
            "brand": "Vendor",
            "manufacturer": "Vendor",
            "product_line": "PETG",
            "material_type": "PETG",
            "region": "global",
        },
        "sources": [
            {
                "source_ref": "source-01",
                "authority": "manufacturer_profile",
                "kind": "json",
                "staged_path": "evidence/vendor-profile.json",
            }
        ],
        "claims": [],
        "conflicts": [],
    }
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report_path = build_profile(
        manifest_path,
        tmp_path / "out",
        bambu_home=_bambu_home(tmp_path),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["manufacturer_profile"]["source_ref"] == "source-01"
    assert report["settings"]["filament_max_volumetric_speed"] == ["12"]
    assert report["settings"]["cool_plate_temp"] == ["65"]


def test_non_04_nozzle_is_blocked(tmp_path: Path) -> None:
    with pytest.raises(ProfileBuildError, match="只允许"):
        build_profile(
            _manifest(tmp_path / "manifest.json"),
            tmp_path / "out",
            nozzle_mm=0.6,
            bambu_home=_bambu_home(tmp_path),
        )


def test_brand_plus_material_does_not_match_a_different_product_line(tmp_path: Path) -> None:
    manifest_path = _manifest(tmp_path / "manifest.json", brand="Polymaker")
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    data["filament"]["product_line"] = "PETG"
    manifest_path.write_text(json.dumps(data), encoding="utf-8")
    report_path = build_profile(
        manifest_path,
        tmp_path / "out",
        bambu_home=_bambu_home(tmp_path, include_polylite=True),
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["official_match"] is None
    assert report["baseline_name"] == "Generic PETG @BBL A1"
