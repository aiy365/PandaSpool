from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import InputError
from .staging import load_manifest
from .util import fingerprint, safe_slug


def record_calibration(
    manifest_file: str | Path,
    calibration_file: str | Path,
    output_root: str | Path,
) -> Path:
    _, manifest = load_manifest(manifest_file)
    source = Path(calibration_file).expanduser().resolve()
    try:
        calibration: Any = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InputError(f"无法读取校准JSON：{source}") from exc
    if not isinstance(calibration, dict):
        raise InputError("校准文件必须是JSON对象。")
    required = ("machine", "nozzle_mm", "test_type", "result")
    missing = [key for key in required if calibration.get(key) in (None, "", {})]
    if missing:
        raise InputError(f"校准文件缺少字段：{missing}")
    if float(calibration["nozzle_mm"]) != 0.4:
        raise InputError("v0.1只记录A1 0.4 mm校准。")
    payload = {
        "schema_version": 1,
        "status": "recorded",
        "created_at": datetime.now(UTC).isoformat(),
        "filament": manifest["filament"],
        "source_snapshot_hash": manifest["manifest_fingerprint"],
        "machine": calibration["machine"],
        "nozzle_mm": calibration["nozzle_mm"],
        "hotend": calibration.get("hotend"),
        "plate": calibration.get("plate"),
        "lot": calibration.get("lot"),
        "drying": calibration.get("drying") or {},
        "environment": calibration.get("environment") or {},
        "test_type": calibration["test_type"],
        "result": calibration["result"],
        "artifact_path": calibration.get("artifact_path"),
    }
    payload["fingerprint"] = fingerprint(payload)
    identity = manifest["filament"]
    output_dir = Path(output_root).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / (
        f"{safe_slug(str(identity['brand']))}-{safe_slug(str(identity['product_line']))}-"
        f"{safe_slug(str(calibration['test_type']))}-{payload['fingerprint'][:8]}.json"
    )
    destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return destination
