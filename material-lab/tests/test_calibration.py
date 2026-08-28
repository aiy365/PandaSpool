from __future__ import annotations

import json
from pathlib import Path

from printpilot_material_lab.calibration import record_calibration


def test_calibration_is_separate_from_manifest(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    original = {
        "schema_version": 1,
        "manifest_fingerprint": "a" * 64,
        "filament": {
            "brand": "R3D",
            "product_line": "PETG Transparent",
            "material_type": "PETG",
            "region": "global",
        },
    }
    manifest.write_text(json.dumps(original), encoding="utf-8")
    calibration = tmp_path / "calibration.json"
    calibration.write_text(
        json.dumps(
            {
                "machine": "Bambu Lab A1",
                "nozzle_mm": 0.4,
                "test_type": "flow_ratio",
                "result": {"accepted": 0.96},
            }
        ),
        encoding="utf-8",
    )

    result = record_calibration(manifest, calibration, tmp_path / "records")
    assert result.is_file()
    assert json.loads(manifest.read_text(encoding="utf-8")) == original
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["result"] == {"accepted": 0.96}
