from __future__ import annotations

import hashlib
import io
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable

from .errors import InputError


EVALUATED_FIELDS = (
    "filament_id",
    "filament_vendor",
    "filament_type",
    "filament_settings_id",
    "filament_flow_ratio",
    "filament_max_volumetric_speed",
    "filament_density",
    "filament_diameter",
    "filament_cost",
    "temperature_vitrification",
    "nozzle_temperature",
    "nozzle_temperature_range_low",
    "nozzle_temperature_range_high",
    "fan_min_speed",
    "fan_max_speed",
    "hot_plate_temp",
    "hot_plate_temp_initial_layer",
    "textured_plate_temp",
    "textured_plate_temp_initial_layer",
    "eng_plate_temp",
    "eng_plate_temp_initial_layer",
    "cool_plate_temp",
    "cool_plate_temp_initial_layer",
    "default_filament_colour",
    "compatible_printers",
)

AUTHORITIES = {"bambu_system", "manufacturer_profile", "user_profile"}


def _scalar(value: Any) -> Any:
    if isinstance(value, list) and len(value) == 1:
        return value[0]
    return value


def _target_entries(filename: str, data: bytes) -> list[tuple[str, dict[str, Any]]]:
    try:
        stream = io.BytesIO(data)
        if zipfile.is_zipfile(stream):
            entries: list[tuple[str, dict[str, Any]]] = []
            with zipfile.ZipFile(stream) as bundle:
                for name in bundle.namelist():
                    if not name.lower().endswith(".json") or name.endswith("bundle_structure.json"):
                        continue
                    payload = json.loads(bundle.read(name).decode("utf-8-sig"))
                    printers = [str(item) for item in payload.get("compatible_printers", [])]
                    profile_name = str(payload.get("name") or name)
                    if "Bambu Lab A1 0.4 nozzle" in profile_name or any(
                        item == "Bambu Lab A1 0.4 nozzle" for item in printers
                    ):
                        entries.append((name, payload))
            if not entries:
                raise InputError(f"{filename}中没有Bambu Lab A1 0.4 mm耗材预设。")
            return entries
        return [(filename, json.loads(data.decode("utf-8-sig")))]
    except (OSError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile) as exc:
        raise InputError(f"无法解析耗材预设：{filename}。") from exc


def _local_profile_root(source_path: str) -> Path:
    path = Path(source_path).resolve().parent
    for candidate in (path, *path.parents):
        if candidate.name.casefold() == "filament":
            return candidate
    return path


def _expanded_local_profile(
    payload: dict[str, Any], source_path: str | None
) -> tuple[dict[str, Any], list[str]]:
    """Expand a Bambu JSON inheritance chain when its local tree is available."""

    if not source_path or Path(source_path).suffix.casefold() != ".json":
        return payload, []
    root = _local_profile_root(source_path)
    chain: list[str] = []
    active: set[str] = set()

    def expand(current: dict[str, Any]) -> dict[str, Any]:
        parent_name = str(current.get("inherits") or "").strip()
        if not parent_name:
            return dict(current)
        if parent_name in active:
            raise InputError(f"耗材预设继承出现循环：{parent_name}。")
        active.add(parent_name)
        candidates = sorted(root.rglob(f"{parent_name}.json"))
        if len(candidates) != 1:
            active.remove(parent_name)
            return dict(current)
        try:
            parent_payload = json.loads(candidates[0].read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise InputError(f"无法解析父级耗材预设：{parent_name}。") from exc
        expanded = expand(parent_payload)
        chain.append(parent_name)
        expanded.update(current)
        active.remove(parent_name)
        return expanded

    return expand(payload), chain


def _color_hint(path: Path, profile_name: str) -> str | None:
    candidate = f"{path.stem} {profile_name}".casefold()
    matches = (
        (("transparent", "clear", "透明"), "透明"),
        (("white", "白色"), "白色"),
        (("black", "黑色"), "黑色"),
    )
    for terms, label in matches:
        if any(term in candidate for term in terms):
            return label
    return None


def _printer_and_nozzle(payload: dict[str, Any], profile_name: str) -> tuple[str, float]:
    printers = payload.get("compatible_printers") or []
    printer = str(printers[0]) if printers else profile_name
    match = re.search(r"(.+?)\s+(\d+(?:\.\d+)?)\s+nozzle", printer)
    if not match:
        return printer, 0.4
    return match.group(1).strip(), float(match.group(2))


def evaluate_preset_file(
    filename: str | Path,
    *,
    authority: str = "user_profile",
    provenance: str | None = None,
) -> dict[str, Any]:
    path = Path(filename).expanduser().resolve()
    if not path.is_file():
        raise InputError(f"预设文件不存在：{path}。")
    return evaluate_preset_bytes(
        path.name,
        path.read_bytes(),
        source_path=str(path),
        authority=authority,
        provenance=provenance,
    )


def evaluate_preset_bytes(
    filename: str,
    data: bytes,
    *,
    source_path: str | None = None,
    authority: str = "user_profile",
    provenance: str | None = None,
) -> dict[str, Any]:
    if authority not in AUTHORITIES:
        raise InputError("预设来源级别无效。")
    digest = hashlib.sha256(data).hexdigest()
    source_name = Path(filename).name
    profiles: list[dict[str, Any]] = []
    for entry_name, payload in _target_entries(source_name, data):
        profile_name = str(payload.get("name") or Path(source_name).stem)
        expanded_payload, inheritance_chain = _expanded_local_profile(payload, source_path)
        printer, nozzle_mm = _printer_and_nozzle(expanded_payload, profile_name)
        color = _color_hint(Path(source_name), profile_name)
        settings = {
            key: _scalar(expanded_payload[key])
            for key in EVALUATED_FIELDS
            if key in expanded_payload
        }
        warnings = []
        internal_origin = str(payload.get("from") or "unknown")
        if internal_origin.casefold() == "user":
            warnings.append(
                "文件内部标记为User；来源身份依赖外部提供链，不等同于拓竹系统预设。"
            )
        if str(settings.get("cool_plate_temp", "")) == "0":
            warnings.append(
                "低温板字段为0；使用BIQU Glacier时必须按冰川策略另行评估。"
            )
        if inheritance_chain:
            warnings.append(f"已展开继承链：{' → '.join(inheritance_chain)}。")
        profiles.append(
            {
                "entry": entry_name,
                "profile_name": profile_name,
                "vendor": _scalar(expanded_payload.get("filament_vendor")),
                "material_type": _scalar(expanded_payload.get("filament_type")),
                "target_printer": printer,
                "nozzle_mm": nozzle_mm,
                "scope_level": "color_variant" if color else "product",
                "color": color,
                "authority": authority,
                "provenance": provenance or "用户提供，来源待核验",
                "internal_origin": internal_origin,
                "settings": settings,
                "warnings": warnings,
            }
        )
    return {
        "file": source_path,
        "filename": source_name,
        "sha256": digest,
        "container": "bbsflmt" if zipfile.is_zipfile(io.BytesIO(data)) else "json",
        "profiles": profiles,
    }


def evaluate_preset_files(
    filenames: Iterable[str | Path],
    *,
    authority: str = "user_profile",
    provenance: str | None = None,
) -> dict[str, Any]:
    files = [
        evaluate_preset_file(path, authority=authority, provenance=provenance)
        for path in filenames
    ]
    return {
        "files": files,
        "summary": {
            "file_count": len(files),
            "profile_count": sum(len(item["profiles"]) for item in files),
            "product_scoped": sum(
                profile["scope_level"] == "product"
                for item in files
                for profile in item["profiles"]
            ),
            "color_scoped": sum(
                profile["scope_level"] == "color_variant"
                for item in files
                for profile in item["profiles"]
            ),
        },
    }
