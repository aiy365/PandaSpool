from __future__ import annotations

import json
import os
import subprocess
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import InputError, ProfileBuildError
from .staging import load_manifest
from .util import fingerprint, safe_slug, scalar, sha256_file


TARGET_PRINTER = "Bambu Lab A1 0.4 nozzle"
SUPPORTED_NOZZLE_MM = 0.4
DEFAULT_BAMBU_HOME = Path(r"C:\Program Files\Bambu Studio")

PLATE_POLICIES = {
    "glacier": {
        "name": "BIQU Glacier（必趣 冰川）",
        "evidence": {
            "title": "用户提供的BIQU Glacier参数图（2026-08-10）",
            "filename": "codex-clipboard-d3bb7a9a-edcb-4ac4-beab-3f56d8706345.png",
            "sha256": "d930e7ce08656a2db3a2dc8be9dc97dbff5ecd102d1ae78e4249e3bbd64f7c3e",
        },
        "materials": {
            "PLA": {"range_c": [45, 55], "default_c": 50},
            "PETG": {"range_c": [60, 75], "default_c": 65},
        },
        "fields": ("cool_plate_temp", "cool_plate_temp_initial_layer"),
    }
}

PROFILE_FIELD_RULES = {
    "density_g_cm3": "filament_density",
    "nozzle_temperature_c": "nozzle_temperature",
    "nozzle_temperature_range_c": (
        "nozzle_temperature_range_low",
        "nozzle_temperature_range_high",
    ),
    "bed_temperature_range_c": "__bed_temperature_range__",
    "fan_speed_range_percent": "__fan_speed_range__",
    "filament_max_volumetric_speed_mm3_s": "filament_max_volumetric_speed",
    "filament_flow_ratio": "filament_flow_ratio",
}

THROUGHPUT_AUTHORITIES = {"manufacturer_profile", "bambu_system", "calibration"}

RANGE_CONSTRAINTS = {
    "__bed_temperature_range__": {
        "fields": (
            "eng_plate_temp",
            "eng_plate_temp_initial_layer",
            "hot_plate_temp",
            "hot_plate_temp_initial_layer",
            "textured_plate_temp",
            "textured_plate_temp_initial_layer",
        ),
        "unit": "°C",
    },
    "__fan_speed_range__": {
        "fields": ("fan_min_speed", "fan_max_speed"),
        "unit": "%",
    },
}


def _normalize(value: str | None) -> str:
    return " ".join((value or "").casefold().replace("_", " ").replace("-", " ").split())


class BambuProfiles:
    def __init__(self, bambu_home: str | Path | None = None) -> None:
        home = Path(bambu_home or os.environ.get("BAMBU_STUDIO_HOME") or DEFAULT_BAMBU_HOME)
        self.home = home.expanduser().resolve()
        self.executable = self.home / "bambu-studio.exe"
        self.root = self.home / "resources" / "profiles" / "BBL" / "filament"
        if not self.executable.is_file() or not self.root.is_dir():
            raise ProfileBuildError(f"Bambu Studio安装不完整：{self.home}")
        self._name_index: dict[str, list[Path]] | None = None

    def _index(self) -> dict[str, list[Path]]:
        if self._name_index is None:
            index: dict[str, list[Path]] = {}
            for path in self.root.rglob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    continue
                name = str(data.get("name", path.stem))
                index.setdefault(name, []).append(path)
            self._name_index = index
        return self._name_index

    def _parent_path(self, child: Path, parent_name: str) -> Path:
        same_dir = child.parent / f"{parent_name}.json"
        if same_dir.is_file():
            return same_dir
        matches = self._index().get(parent_name, [])
        if len(matches) == 1:
            return matches[0]
        if not matches:
            raise ProfileBuildError(f"找不到耗材预设继承项：{parent_name}")
        raise ProfileBuildError(f"耗材预设继承项不唯一：{parent_name}")

    def flatten(self, path: Path) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        seen: set[str] = set()
        current = path
        while True:
            try:
                data = json.loads(current.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProfileBuildError(f"无法读取Bambu预设：{current}") from exc
            name = str(data.get("name", current.stem))
            if name in seen:
                raise ProfileBuildError(f"耗材预设继承形成循环：{name}")
            seen.add(name)
            merged = {**data, **merged}
            parent = data.get("inherits")
            if not parent:
                break
            current = self._parent_path(current, str(parent))
        merged.pop("inherits", None)
        return merged

    def compatible_profiles(self, material_type: str) -> list[tuple[Path, dict[str, Any]]]:
        results: list[tuple[Path, dict[str, Any]]] = []
        for path in self.root.rglob("*.json"):
            if "@BBL A1" not in path.stem:
                continue
            try:
                data = self.flatten(path)
            except ProfileBuildError:
                continue
            printers = list(data.get("compatible_printers", []) or [])
            if TARGET_PRINTER not in printers:
                continue
            if _normalize(scalar(data.get("filament_type"))) != _normalize(material_type):
                continue
            results.append((path, data))
        return results

    def exact_vendor_match(
        self, identity: dict[str, Any]
    ) -> tuple[Path, dict[str, Any]] | None:
        brand_values = {
            _normalize(str(identity.get("brand") or "")),
            _normalize(str(identity.get("manufacturer") or "")),
        } - {""}
        product = _normalize(str(identity.get("product_line") or ""))
        material = _normalize(str(identity.get("material_type") or ""))
        candidates: list[tuple[int, Path, dict[str, Any]]] = []
        for path, profile in self.compatible_profiles(str(identity["material_type"])):
            vendor = _normalize(scalar(profile.get("filament_vendor")))
            name = _normalize(str(profile.get("name") or path.stem))
            if vendor not in brand_values:
                continue
            product_tokens = [token for token in product.split() if len(token) > 1]
            expected_names = {
                _normalize(f"{brand} {product}")
                for brand in brand_values
                if brand and not product.startswith(brand)
            }
            expected_names.add(product)
            exact_name_match = any(
                expected and name.startswith(expected) for expected in expected_names
            )
            distinctive_tokens = [
                token
                for token in product_tokens
                if token not in set(material.split()) and token not in brand_values
            ]
            distinctive_match = bool(distinctive_tokens) and all(
                token in name for token in distinctive_tokens
            )
            if not exact_name_match and not distinctive_match:
                continue
            score = sum(10 for token in product_tokens if token in name)
            score += 100 if exact_name_match else 0
            score += 20 if any(name.startswith(brand) for brand in brand_values) else 0
            score -= len(name)
            candidates.append((score, path, profile))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0], reverse=True)
        if len(candidates) > 1 and candidates[0][0] == candidates[1][0]:
            raise ProfileBuildError(
                "发现多个同等匹配的Bambu官方耗材预设，不能自动替用户选择："
                + "、".join(str(item[2].get("name")) for item in candidates[:5])
            )
        _, path, profile = candidates[0]
        return path, profile

    def baseline(self, identity: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
        material = str(identity["material_type"]).upper()
        descriptor = _normalize(
            " ".join(
                str(identity.get(key) or "")
                for key in ("product_line", "variant", "color")
            )
        )
        preferred: list[str] = []
        if any(token in descriptor for token in ("transparent", "translucent", "clear", "透明")):
            preferred.append(f"Bambu {material} Translucent @BBL A1.json")
        if any(token in descriptor for token in ("matte", "哑光", "磨砂")):
            preferred.append(f"Bambu {material} Matte @BBL A1.json")
        descriptor_tokens = set(descriptor.split())
        if (
            "hf" in descriptor_tokens
            or "high flow" in descriptor
            or "high speed" in descriptor
            or "高速" in descriptor
        ):
            preferred.append(f"Bambu {material} HF @BBL A1.json")
        preferred.append(f"Generic {material} @BBL A1.json")
        for filename in preferred:
            path = self.root / filename
            if path.is_file():
                profile = self.flatten(path)
                if TARGET_PRINTER in list(profile.get("compatible_printers", []) or []):
                    return path, profile
        raise ProfileBuildError(
            f"Bambu Studio没有可用的A1 0.4 {material}基线预设。"
        )


def _matches_identity(profile: dict[str, Any], identity: dict[str, Any]) -> bool:
    if TARGET_PRINTER not in list(profile.get("compatible_printers", []) or []):
        return False
    if _normalize(scalar(profile.get("filament_type"))) != _normalize(
        str(identity["material_type"])
    ):
        return False
    vendors = {
        _normalize(str(identity.get("brand") or "")),
        _normalize(str(identity.get("manufacturer") or "")),
    } - {""}
    if _normalize(scalar(profile.get("filament_vendor"))) not in vendors:
        return False
    name = _normalize(str(profile.get("name") or ""))
    product_tokens = [
        token
        for token in _normalize(str(identity.get("product_line") or "")).split()
        if len(token) > 1
    ]
    return not product_tokens or all(token in name for token in product_tokens)


def _manufacturer_profile(
    manifest_path: Path,
    manifest: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[str, dict[str, Any], str, dict[str, Any]] | None:
    candidates: list[tuple[str, dict[str, Any], str, dict[str, Any]]] = []
    for source in manifest.get("sources", []):
        if source.get("authority") != "manufacturer_profile":
            continue
        evidence_path = manifest_path.parent / str(source["staged_path"])
        profiles: list[tuple[str, dict[str, Any]]] = []
        if source.get("kind") == "json":
            try:
                data = json.loads(evidence_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProfileBuildError(f"无法读取厂家预设：{evidence_path}") from exc
            if isinstance(data, dict):
                profiles.append((evidence_path.name, data))
        elif source.get("kind") == "bbsflmt":
            try:
                with zipfile.ZipFile(evidence_path) as archive:
                    for name in archive.namelist():
                        if not name.lower().endswith(".json") or name == "bundle_structure.json":
                            continue
                        data = json.loads(archive.read(name).decode("utf-8"))
                        if isinstance(data, dict):
                            profiles.append((name, data))
            except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProfileBuildError(f"无法读取厂家BBSFLMT：{evidence_path}") from exc
        for entry_name, profile in profiles:
            if not _matches_identity(profile, identity):
                continue
            narrowed = dict(profile)
            narrowed["compatible_printers"] = [TARGET_PRINTER]
            validate_profile(narrowed)
            candidates.append(
                (
                    f"{evidence_path}::{entry_name}",
                    narrowed,
                    fingerprint(narrowed),
                    source,
                )
            )
    if not candidates:
        return None
    if len(candidates) > 1:
        raise ProfileBuildError(
            "找到多个同等匹配的厂家A1 0.4预设，不能自动选择："
            + "、".join(candidate[0] for candidate in candidates[:5])
        )
    return candidates[0]


def _approved_claims(manifest: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for claim in manifest.get("claims", []):
        if claim.get("review_status") == "approved":
            grouped.setdefault(str(claim["key"]), []).append(claim)
    return grouped


def _conflict_keys(manifest: dict[str, Any]) -> set[str]:
    return {str(item["key"]) for item in manifest.get("conflicts", [])}


def _single_claim(
    grouped: dict[str, list[dict[str, Any]]], conflicts: set[str], key: str
) -> dict[str, Any] | None:
    if key in conflicts:
        return None
    claims = grouped.get(key, [])
    if not claims:
        return None
    signatures = {json.dumps(claim["value"], ensure_ascii=False, sort_keys=True) for claim in claims}
    if len(signatures) != 1:
        return None
    return claims[0]


def _as_number_list(value: Any, length: int) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise ProfileBuildError(f"参数值必须包含{length}个数字：{value!r}")
    try:
        return [float(item) for item in value]
    except (TypeError, ValueError) as exc:
        raise ProfileBuildError(f"参数值必须包含{length}个数字：{value!r}") from exc


def _apply_range_constraint(
    output: dict[str, Any],
    claim: dict[str, Any],
    marker: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    low, high = _as_number_list(claim["value"], 2)
    if low > high:
        raise ProfileBuildError(f"范围下限不得高于上限：{claim['key']}")
    rule = RANGE_CONSTRAINTS[marker]
    changes: list[dict[str, Any]] = []
    checked: list[str] = []
    for field in rule["fields"]:
        raw = output.get(field)
        if not isinstance(raw, list) or not raw:
            continue
        try:
            before_values = [float(item) for item in raw]
        except (TypeError, ValueError) as exc:
            raise ProfileBuildError(f"Bambu基线字段不是数字列表：{field}") from exc
        after_values = [min(max(value, low), high) for value in before_values]
        checked.append(field)
        after = [f"{value:g}" for value in after_values]
        if raw != after:
            output[field] = after
            changes.append(
                {
                    "field": field,
                    "before": raw,
                    "after": after,
                    "claim_key": claim["key"],
                    "source_ref": claim["source_ref"],
                    "method": "收敛到厂家声明范围",
                }
            )
    return changes, {
        "key": claim["key"],
        "source_ref": claim["source_ref"],
        "range": [low, high],
        "unit": rule["unit"],
        "checked_fields": checked,
        "result": "baseline_within_range" if not changes else "outliers_clamped",
    }


def _apply_claims(
    baseline: dict[str, Any], manifest: dict[str, Any]
) -> tuple[
    dict[str, Any],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    output = dict(baseline)
    grouped = _approved_claims(manifest)
    conflicts = _conflict_keys(manifest)
    changes: list[dict[str, Any]] = []
    ignored: list[dict[str, Any]] = []
    verified: list[dict[str, Any]] = []

    for key, target in PROFILE_FIELD_RULES.items():
        claim = _single_claim(grouped, conflicts, key)
        if not claim:
            if key in conflicts:
                ignored.append({"key": key, "reason": "存在未解决冲突"})
            continue
        if key in {"filament_max_volumetric_speed_mm3_s", "filament_flow_ratio"}:
            if claim.get("authority") not in THROUGHPUT_AUTHORITIES:
                ignored.append(
                    {
                        "key": key,
                        "reason": "流量参数只接受厂家机器预设、Bambu系统预设或实测校准",
                    }
                )
                continue
        if isinstance(target, str) and target in RANGE_CONSTRAINTS:
            range_changes, verification = _apply_range_constraint(output, claim, target)
            changes.extend(range_changes)
            verified.append(verification)
            continue
        if isinstance(target, tuple):
            values = _as_number_list(claim["value"], len(target))
            for field, value in zip(target, values, strict=True):
                before = output.get(field)
                after = [f"{value:g}"]
                output[field] = after
                if before != after:
                    changes.append(
                        {
                            "field": field,
                            "before": before,
                            "after": after,
                            "claim_key": key,
                            "source_ref": claim["source_ref"],
                        }
                    )
        else:
            try:
                value = float(claim["value"])
            except (TypeError, ValueError) as exc:
                raise ProfileBuildError(f"{key} 必须是数字。") from exc
            before = output.get(target)
            after = [f"{value:g}"]
            output[target] = after
            if before != after:
                changes.append(
                    {
                        "field": target,
                        "before": before,
                        "after": after,
                        "claim_key": key,
                        "source_ref": claim["source_ref"],
                    }
                )

    for key in grouped:
        if key not in PROFILE_FIELD_RULES:
            ignored.append({"key": key, "reason": "不是A1耗材预设白名单字段"})
    return output, changes, ignored, verified


def _apply_plate_policy(
    settings: dict[str, Any], material_type: str, policy_id: str
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if policy_id == "baseline":
        return [], None
    policy = PLATE_POLICIES.get(policy_id)
    if not policy:
        raise ProfileBuildError(f"未知打印板策略：{policy_id}")
    material = material_type.upper()
    material_policy = policy["materials"].get(material)
    if not material_policy:
        raise ProfileBuildError(
            f"{policy['name']}策略尚未定义{material}温度；不能自动猜测。"
        )
    target = float(material_policy["default_c"])
    changes: list[dict[str, Any]] = []
    for field in policy["fields"]:
        before = settings.get(field)
        after = [f"{target:g}"]
        settings[field] = after
        if before != after:
            changes.append(
                {
                    "field": field,
                    "before": before,
                    "after": after,
                    "claim_key": "build_plate_temperature_c",
                    "source_ref": "plate-policy:glacier",
                    "method": "Glacier低温增稳板默认起点",
                }
            )
    return changes, {
        "id": policy_id,
        "name": policy["name"],
        "material": material,
        "range_c": material_policy["range_c"],
        "default_c": material_policy["default_c"],
        "fields": list(policy["fields"]),
        "evidence": policy["evidence"],
        "assumption": "范围中点作为首轮起点；实测结果进入个人校准层。",
    }


def validate_profile(settings: dict[str, Any]) -> None:
    required = (
        "name",
        "filament_type",
        "filament_vendor",
        "filament_flow_ratio",
        "filament_max_volumetric_speed",
        "nozzle_temperature",
        "compatible_printers",
    )
    missing = [key for key in required if not settings.get(key)]
    if missing:
        raise ProfileBuildError(f"生成预设缺少必需字段：{missing}")
    if list(settings.get("compatible_printers", []) or []) != [TARGET_PRINTER]:
        raise ProfileBuildError("生成预设必须且只能声明A1 0.4兼容。")
    for key in ("filament_flow_ratio", "filament_max_volumetric_speed", "nozzle_temperature"):
        try:
            if float(scalar(settings.get(key)) or "0") <= 0:
                raise ValueError
        except ValueError as exc:
            raise ProfileBuildError(f"生成预设字段不是有效正数：{key}") from exc


def _write_bundle(profile: dict[str, Any], destination: Path, studio_version: str) -> None:
    vendor = str(scalar(profile.get("filament_vendor")) or "PrintPilot")
    name = str(profile["name"])
    profile_path = f"{safe_slug(vendor)}/{name}.json"
    structure = {
        "bundle_id": f"printpilot_{fingerprint(profile)[:16]}",
        "bundle_type": "filament config bundle",
        "filament_name": name.split(" @Bambu", 1)[0],
        "filament_vendor": [{"filament_path": [profile_path], "vendor": vendor}],
        "version": studio_version,
    }
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(profile_path, json.dumps(profile, ensure_ascii=False, indent=2))
        archive.writestr("bundle_structure.json", json.dumps(structure, ensure_ascii=False, indent=2))


def _write_report(report: dict[str, Any], path: Path) -> None:
    identity = report["filament"]
    lines = [
        f"# {identity['brand']} {identity['product_line']} A1 0.4预设报告",
        "",
        f"- 结论：**{report['decision']}**",
        f"- 状态：{report['status']}",
        f"- Bambu基线：`{report.get('baseline_name') or '不适用'}`",
        "",
    ]
    if report.get("plate_policy"):
        plate = report["plate_policy"]
        lines.extend(
            [
                "## 打印板策略",
                "",
                f"- 打印板：`{plate['name']}`",
                f"- 厂家范围：{plate['range_c'][0]}–{plate['range_c'][1]} °C",
                f"- 首轮起点：{plate['default_c']} °C",
                f"- 说明：{plate['assumption']}",
                "",
            ]
        )
    if report.get("manufacturer_profile"):
        manufacturer = report["manufacturer_profile"]
        lines.extend(
            [
                "## 厂家预设",
                "",
                f"使用厂家提供且明确兼容A1 0.4的 `{manufacturer['name']}` 作为基线。",
                f"来源：`{manufacturer['source_ref']}`。",
                "",
            ]
        )
    if report.get("official_match") and not report.get("generated_json"):
        lines.extend(
            [
                "## 官方匹配",
                "",
                f"Bambu Studio已包含 `{report['official_match']['name']}`，不生成重复自定义预设。",
                "",
            ]
        )
    else:
        if report.get("official_match"):
            lines.extend(
                [
                    "## 官方基线",
                    "",
                    f"Bambu Studio内置 `{report['official_match']['name']}` 作为基线；"
                    "自定义版本只叠加个人打印板策略。",
                    "",
                ]
            )
        lines.extend(["## 参数改动", ""])
        if report["changes"]:
            lines.append("| 字段 | 原值 | 新值 | 来源 |")
            lines.append("|---|---|---|---|")
            for change in report["changes"]:
                lines.append(
                    f"| `{change['field']}` | `{change['before']}` | `{change['after']}` | "
                    f"`{change['source_ref']}` |"
                )
        else:
            lines.append("供应商声明均在官方基线范围内，未覆盖工艺字段。")
        lines.extend(["", "## 范围验证", ""])
        if report.get("verified_claims"):
            for item in report["verified_claims"]:
                result = (
                    "基线已在范围内，保持官方值"
                    if item["result"] == "baseline_within_range"
                    else "越界值已收敛到厂家范围"
                )
                lines.append(
                    f"- `{item['key']}`：{item['range'][0]:g}–{item['range'][1]:g}"
                    f" {item['unit']}；{result}；来源 `{item['source_ref']}`"
                )
        lines.extend(["", "## 未采用声明", ""])
        for item in report["ignored_claims"]:
            lines.append(f"- `{item['key']}`：{item['reason']}")
        lines.extend(
            [
                "",
                "## 校准清单",
                "",
                "1. 确认材料已按厂家要求烘干。",
                "2. 运行流量比例校准。",
                "3. 记录K/PA，但不要回写厂家事实。",
                "4. 运行最大体积流量测试；完成前沿用基线MVS。",
                "5. 用真实模型切片并检查透明效果、拉丝和层间结合。",
            ]
        )
        validation = report.get("validation") or {}
        lines.extend(
            [
                "",
                "## 切片验证",
                "",
                f"- 结构校验：`{validation.get('profile_structure', 'not_run')}`",
                f"- 真实切片：`{validation.get('slice', 'not_run')}`",
            ]
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_profile(
    manifest_file: str | Path,
    output_root: str | Path,
    nozzle_mm: float = 0.4,
    bambu_home: str | Path | None = None,
    studio_version: str = "02.08.01.55",
    plate_policy: str = "glacier",
) -> Path:
    if abs(nozzle_mm - SUPPORTED_NOZZLE_MM) > 1e-9:
        raise ProfileBuildError("v0.1只允许生成A1 0.4 mm预设；0.6和0.2尚未开放。")
    manifest_path, manifest = load_manifest(manifest_file)
    identity = manifest["filament"]
    profiles = BambuProfiles(bambu_home)
    run_dir = Path(output_root).expanduser().resolve() / (
        f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-"
        f"{safe_slug(str(identity['brand']))}-{safe_slug(str(identity['product_line']))}-"
        f"{str(manifest['manifest_fingerprint'])[:8]}"
    )
    run_dir.mkdir(parents=True, exist_ok=False)

    official = profiles.exact_vendor_match(identity)
    manufacturer = None if official else _manufacturer_profile(manifest_path, manifest, identity)
    if official and plate_policy == "baseline":
        official_path, official_profile = official
        report = {
            "schema_version": 1,
            "status": "official_profile_available",
            "decision": "直接使用Bambu Studio官方匹配预设",
            "filament": identity,
            "manifest": str(manifest_path),
            "official_match": {
                "name": official_profile["name"],
                "path": str(official_path),
                "sha256": sha256_file(official_path),
            },
            "baseline_name": official_profile["name"],
            "changes": [],
            "ignored_claims": [],
        }
    else:
        if official:
            baseline_path, baseline = official
            baseline_path_text = str(baseline_path)
            baseline_sha256 = sha256_file(baseline_path)
            generated = dict(baseline)
            changes: list[dict[str, Any]] = []
            verified: list[dict[str, Any]] = []
            ignored = [
                {"key": key, "reason": "Bambu Studio完全匹配预设优先，未覆盖官方工艺字段"}
                for key in sorted(_approved_claims(manifest))
            ]
            decision = "基于Bambu官方匹配预设生成Glacier派生草案"
            official_match = {
                "name": baseline["name"],
                "path": str(baseline_path),
                "sha256": sha256_file(baseline_path),
                "used_as_baseline": True,
            }
            manufacturer_match = None
        elif manufacturer:
            baseline_path_text, baseline, baseline_sha256, manufacturer_source = manufacturer
            generated = dict(baseline)
            changes = []
            verified = []
            ignored = [
                {"key": key, "reason": "厂家目标机器预设优先，未覆盖其工艺字段"}
                for key in sorted(_approved_claims(manifest))
            ]
            decision = "采用厂家A1 0.4预设并叠加个人打印板策略"
            official_match = None
            manufacturer_match = {
                "name": baseline["name"],
                "path": baseline_path_text,
                "sha256": baseline_sha256,
                "source_ref": manufacturer_source["source_ref"],
            }
        else:
            baseline_path, baseline = profiles.baseline(identity)
            baseline_path_text = str(baseline_path)
            baseline_sha256 = sha256_file(baseline_path)
            generated, changes, ignored, verified = _apply_claims(baseline, manifest)
            decision = "生成保守草案；打印前必须校准"
            official_match = None
            manufacturer_match = None
        plate_changes, selected_plate_policy = _apply_plate_policy(
            generated, str(identity["material_type"]), plate_policy
        )
        changes.extend(plate_changes)
        plate_suffix = " Glacier" if selected_plate_policy else ""
        profile_name = (
            f"{identity['brand']} {identity['product_line']}{plate_suffix} "
            "@Bambu Lab A1 0.4 nozzle"
        )
        build_context_hash = fingerprint(
            {
                "manifest": manifest["manifest_fingerprint"],
                "plate_policy": selected_plate_policy,
                "baseline_sha256": baseline_sha256,
            }
        )
        unique_id = f"PPL{build_context_hash[:8].upper()}"
        generated.update(
            {
                "type": "filament",
                "name": profile_name,
                "from": "User",
                "instantiation": "true",
                "filament_id": unique_id,
                "setting_id": f"{unique_id}_A104",
                "filament_settings_id": [profile_name],
                "filament_vendor": [str(identity["brand"])],
                "filament_type": [str(identity["material_type"])],
                "compatible_printers": [TARGET_PRINTER],
            }
        )
        generated.pop("inherits", None)
        validate_profile(generated)
        json_path = run_dir / f"{safe_slug(profile_name)}.json"
        json_path.write_text(json.dumps(generated, ensure_ascii=False, indent=2), encoding="utf-8")
        bundle_path = run_dir / f"{safe_slug(identity['brand'])}-{safe_slug(identity['product_line'])}-A1-0.4.bbsflmt"
        _write_bundle(generated, bundle_path, studio_version)
        report = {
            "schema_version": 1,
            "status": "draft_needs_calibration",
            "decision": decision,
            "filament": identity,
            "manifest": str(manifest_path),
            "official_match": official_match,
            "manufacturer_profile": manufacturer_match,
            "baseline_name": baseline["name"],
            "baseline_path": baseline_path_text,
            "baseline_sha256": baseline_sha256,
            "generated_json": str(json_path),
            "generated_bbsflmt": str(bundle_path),
            "settings": generated,
            "changes": changes,
            "ignored_claims": ignored,
            "verified_claims": verified,
            "plate_policy": selected_plate_policy,
            "source_manifest_hash": manifest["manifest_fingerprint"],
            "source_snapshot_hash": build_context_hash,
            "generator_version": "0.1.0",
            "validation": {"profile_structure": "passed", "slice": "not_run"},
        }
    report_path = run_dir / "profile-report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_report(report, run_dir / "profile-report.md")
    return report_path


def smoke_slice(
    profile_json: str | Path,
    source_3mf: str | Path,
    output_dir: str | Path,
    bambu_home: str | Path | None = None,
    plate: int = 1,
    timeout_seconds: int = 180,
    report_file: str | Path | None = None,
) -> dict[str, Any]:
    profiles = BambuProfiles(bambu_home)
    profile_path = Path(profile_json).expanduser().resolve()
    source_path = Path(source_3mf).expanduser().resolve()
    if not profile_path.is_file() or not source_path.is_file():
        raise InputError("切片验证需要存在的预设JSON和3MF。")
    settings = json.loads(profile_path.read_text(encoding="utf-8"))
    validate_profile(settings)
    run_dir = Path(output_dir).expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=False)
    output_path = run_dir / f"{source_path.stem}-material-lab-smoke.3mf"
    command = [
        str(profiles.executable),
        "--debug",
        "5",
        "--load-filaments",
        str(profile_path),
        "--slice",
        str(plate),
        "--export-3mf",
        str(output_path),
        "--export-slicedata",
        str(run_dir),
        str(source_path),
    ]
    subprocess.Popen(
        command,
        cwd=run_dir,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    )
    deadline = time.monotonic() + timeout_seconds
    result_path = run_dir / "result.json"
    while time.monotonic() < deadline:
        if output_path.is_file() and result_path.is_file():
            break
        time.sleep(0.25)
    if not output_path.is_file() or not result_path.is_file():
        raise ProfileBuildError("Bambu Studio切片验证超时或未产生结果。")
    result = json.loads(result_path.read_text(encoding="utf-8"))
    smoke_result = {
        "status": "passed",
        "output_3mf": str(output_path),
        "result_json": str(result_path),
        "profile_name": settings["name"],
        "raw_result": result,
    }
    if report_file:
        report_path = Path(report_file).expanduser().resolve()
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InputError(f"无法读取预设报告：{report_path}") from exc
        expected_profile = Path(str(report.get("generated_json") or "")).resolve()
        if expected_profile != profile_path:
            raise InputError("切片预设与待回写的预设报告不一致。")
        report["status"] = "slice_validated"
        report["validation"] = {
            **dict(report.get("validation") or {}),
            "slice": "passed",
            "sliced_at": datetime.now(UTC).isoformat(),
            "source_3mf": str(source_path),
            "output_3mf": str(output_path),
            "result_json": str(result_path),
        }
        report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        _write_report(report, report_path.with_suffix(".md"))
        smoke_result["updated_report"] = str(report_path)
    return smoke_result
